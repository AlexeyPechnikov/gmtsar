# ----------------------------------------------------------------------------
# PyGMTSAR
# 
# This file is part of the PyGMTSAR project: https://github.com/mobigroup/gmtsar
# 
# Copyright (c) 2023, Alexey Pechnikov
# 
# Licensed under the BSD 3-Clause License (see LICENSE for details)
# ----------------------------------------------------------------------------
from .tqdm_joblib import tqdm_joblib

class S1(tqdm_joblib):
    import pandas as pd
    from datetime import timedelta

    http_timeout = 30
    #https://s1orbits.pechnikov.workers.dev/S1A/2014/04/07/index.csv
    #https://s1orbits.pechnikov.workers.dev/S1A/2014/04/07/S1A_OPER_AUX_POEORB_OPOD_20210301T130653_V20140406T225944_20140408T005944.EOF.zip
    orbits_url = 'https://s1orbits.pechnikov.workers.dev/{mission}/{year}/{month:02}/{day:02}/'
    # see _select_orbit.py in sentineleof package
    #Orbital period of Sentinel-1 in seconds
    #T_ORBIT = (12 * 86400.0) / 175.0
    # ESA orbits doe not follow the specification and some orbits are missed
    # example scene: S1A_IW_SLC__1SDV_20240505T002709_20240505T002733_053728_06870F_8D20
    #orbit_offset_start = timedelta(seconds=(12 * 86400.0) // 175.0 + 60)
    # less strict rule allows to find the required orbits
    orbit_offset_start = timedelta(seconds=3600)
    orbit_offset_end = timedelta(seconds=300)

    @staticmethod
    def download_orbits(basedir: str, scenes: list | pd.DataFrame,
                        n_jobs: int = 8, joblib_backend='loky', skip_exist: bool = True,
                        retries: int = 30, timeout_second: float = 3):
        """
        Downloads orbit files corresponding to the specified Sentinel-1 scenes.
    
        Parameters
        ----------
        basedir : str
            The directory where the downloaded orbit files will be saved.
        scenes : list or pandas.DataFrame
            List of scene identifiers or a DataFrame containing scenes for which the orbits are to be downloaded.
        n_jobs : int, optional
            The number of concurrent download jobs. Default is 8.
        joblib_backend : str, optional
            The backend for parallel processing. Default is 'loky'.
        skip_exist : bool, optional
            If True, skips downloading orbits that already exist. Default is True.
    
        Returns
        -------
        pandas.Series
            A Series containing the names of the downloaded orbit files.
    
        Raises
        ------
        ValueError
            If an invalid scenes argument is provided or no suitable orbit files are found.
        """
        import pandas as pd
        import requests
        import os
        import re
        import glob
        from datetime import datetime
        import time
        import joblib
        import zipfile
        from io import BytesIO
        import xmltodict
        from tqdm.auto import tqdm
    
        # create the directory if needed
        os.makedirs(basedir, exist_ok=True)
    
        if not skip_exist:
            orbits = glob.glob('*.EOF', root_dir=basedir)
            #print ('orbits', orbits)
            for orbit in orbits:
                os.remove(os.path.join(basedir, orbit))
    
        if isinstance(scenes, pd.DataFrame):
            if skip_exist:
                # ignore scenes with orbits
                df_data = scenes[scenes.orbitpath.isnull()][['mission', 'datetime']].values
            else:
                # process all the scenes
                df_data = scenes[['mission', 'datetime']].values
        elif isinstance(scenes, list):
            df_data = [(scene.split('_')[0], datetime.strptime(scene.split('_')[5],'%Y%m%dT%H%M%S')) for scene in scenes]
        else:
            raise ValueError(f'Expected secenes argument is list or Pandas DataFrame')
        # nothing to do
        if len(df_data) == 0:
            return
        df = pd.DataFrame(df_data, columns=['mission', 'datetime'])
        df['date'] = df['datetime'].dt.date
        df = df.groupby(['date', 'mission'])['datetime'].first().reset_index()
        del df['date']
        
        def download_index(mission, dt, orbit_offset_start, orbit_offset_end):
            url = S1.orbits_url.format(mission=mission,
                                       year=dt.date().year,
                                       month=dt.date().month,
                                       day=dt.date().day)
            #print ('url', url + 'index.csv')
            with requests.get(url + 'index.csv', timeout=S1.http_timeout) as response:
                response.raise_for_status()
                # the most recent orbits preferred
                lines = sorted(response.text.splitlines(), reverse=True)
                orbits = pd.DataFrame(lines, columns=['orbit']).dropna()
                orbits['product']    = orbits['orbit'].apply(lambda name: name.split('_')[3])
                orbits['mission']    = orbits['orbit'].apply(lambda name: name[:3])
                orbits['time']       = orbits['orbit'].apply(lambda name: datetime.strptime(name.split('_')[5], '%Y%m%dT%H%M%S'))
            # detect suitable orbit and select the first one
            for orbit in orbits.itertuples():
                #print ('orbit', orbit)
                orbit_parts = orbit.orbit.split('.')[0].split('_')
                #print ('orbit_parts', orbit_parts)
                if orbit.product == 'RESORB':
                    # select the one covering the interval
                    time_start = datetime.strptime(orbit_parts[6][1:],  '%Y%m%dT%H%M%S') + orbit_offset_start
                    time_end   = datetime.strptime(orbit_parts[7], '%Y%m%dT%H%M%S') - orbit_offset_end
                    #print ('time_start', time_start, 'time_end', time_end)
                    if not ((time_start <= dt) & (time_end >= dt)):
                        continue
                    return (orbit.orbit, url)
                elif orbit.product == 'POEORB':
                    # select the most recent one
                    return (orbit.orbit, url)
                else:
                    # in case of data parse or another error
                    raise ValueError(f'Unexpected orbit product {orbit.product}')
            # downloading is not possible
            raise ValueError(f'Orbit product not found for mission {mission} and timestamp {dt}')
    
        # TODO: unzip files
        def download_orbit(basedir, url):
            filename = os.path.join(basedir, os.path.basename(os.path.splitext(url)[0]))
            #print ('url', url, 'filename', filename)
            with requests.get(url, timeout=S1.http_timeout) as response:
                response.raise_for_status()
                with open(filename, 'wb') as f:
                    with zipfile.ZipFile(BytesIO(response.content), 'r') as zip_in:
                        zip_files = zip_in.namelist()
                        if len(zip_files) == 0:
                            raise Exception('ERROR: Downloaded file is empty zip archive.')
                        if len(zip_files) > 1:
                            raise Exception('NOTE: Downloaded zip archive includes multiple files.')
                        # extract specific file content
                        orbit_content = zip_in.read(zip_files[0])
                        # check XML validity
                        xmltodict.parse(orbit_content)
                        f.write(orbit_content)

        def download_with_retry(func, retries, timeout_second, *args, **kwargs):
            for retry in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f'ERROR: download attempt {retry+1} failed: {e}')
                    if retry + 1 >= retries:
                        raise
                time.sleep(timeout_second)

        # download orbits index files and detect the orbits.
        # joblib reads the class file from disk,
        # and to allow modification of orbit_offset_* on the fly, add them to the arguments
        with S1.tqdm_joblib(tqdm(desc='Downloading Sentinel-1 Orbits Index:', total=len(df))) as progress_bar:
            orbits = joblib.Parallel(n_jobs=n_jobs, backend=joblib_backend)(joblib.delayed(download_with_retry)\
                                    (download_index, retries, timeout_second,
                                    mission=scene.mission,
                                    dt=scene.datetime,
                                    orbit_offset_start=S1.orbit_offset_start,
                                    orbit_offset_end=S1.orbit_offset_end) for scene in df.itertuples())
        # convert to dataframe for processing
        orbits = pd.DataFrame(orbits, columns=['orbit', 'url'])
        # exclude duplicates if needed 
        #orbits = orbits.groupby(['orbit']).first().reset_index()
        
        # download orbits index files and detect the orbits
        with S1.tqdm_joblib(tqdm(desc='Downloading Sentinel-1 Orbits:', total=len(orbits))) as progress_bar:
            joblib.Parallel(n_jobs=n_jobs, backend=joblib_backend)(joblib.delayed(download_with_retry)\
                                    (download_orbit, retries, timeout_second,
                                    basedir=basedir,
                                    url=orbit.url + orbit.orbit) for orbit in orbits.itertuples())
        return orbits['orbit']

    @staticmethod
    def scan_slc(datadir, orbit=None, mission=None, subswath=None, polarization=None, calibration=False):
        """
        Scans the specified directory for Sentinel-1 SLC (Single Look Complex) data and filters it based on the provided parameters.
    
        Parameters
        ----------
        datadir : str
            The directory containing the data files.
        orbit : str, optional
            Filter for orbit direction. Use 'A' for Ascending, 'D' for Descending, or None for no filter. Default is None.
        mission : str, optional
            Filter for mission name. Use 'S1A' for Sentinel-1A, 'S1B' for Sentinel-1B, or None for no filter. Default is None.
        subswath : int, optional
            Filter for subswath number. Use a single or sequential numbers 1, 2, 3, 12, 23, 123, or None for no filter. Default is None.
        polarization : str, optional
            Filter for polarization. Use 'VV', 'VH', 'HH', 'HV', or None for no filter. Default is None.
    
        Returns
        -------
        pandas.DataFrame
            A DataFrame containing metadata about the filtered SLC scenes, including their paths and other relevant properties.
    
        Raises
        ------
        ValueError
            If the filtered scenes contain inconsistencies, such as mismatched .tiff and .xml files, or if invalid filter parameters are provided.
        """
        import os
        import shutil
        from glob import glob
        import pandas as pd
        import geopandas as gpd
        import shapely
        import numpy as np
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        oneday = relativedelta(days=1)

        #text2date('V20171110T225942'), text2date('20171117t145927')
        def text2date(text, as_date=True):
            """
            Convert a text string in the format 'VYYYYMMDDTHHMMSS' or 'YYYYMMDDTHHMMSS' to a datetime object or date object.

            Parameters
            ----------
            text : str
                The text string to convert.
            as_date : bool, optional
                If True, return a date object. If False, return a datetime object. Default is True.

            Returns
            -------
            datetime.date or datetime.datetime
                The converted date or datetime object.
            """
            from datetime import datetime
        
            date_fmt = '%Y%m%dT%H%M%S'
            date_str = text.replace('V','').replace('t','T')
            dt = datetime.strptime(date_str, date_fmt)
            if as_date:
                return dt.date()
            return dt

        def pattern2paths(pattern):
            path_pattern = os.path.join(datadir, '**', pattern)
            paths = glob(path_pattern, recursive=True)
            return paths

        assert orbit is None or orbit=='A' or orbit=='D', \
            'ERROR: use symbol A (Ascending) or D (Descending) for orbit filter'
        assert mission is None or mission=='S1A' or mission=='S1B', \
            'ERROR: use name S1A or S1B for mission filter'
        assert subswath is None or subswath in [1,2,3,12,23,123], \
            'ERROR: use a single or sequential numbers 1, 2, 3, 12, 23, 123 for subswath filter'
        assert polarization is None or polarization in ['VV','VH','HH','HV'], \
            'ERROR: use VV or VH or HH or HV for polarization filter'

        if polarization is None:
            polarization = '??'
        if subswath is None:
            subswath  = '?'
        else:
            subswath = f'[{subswath}]'
        # filter mission
        if mission is not None:
            path_pattern = f'{mission.lower()}-iw{subswath}-slc-{polarization.lower()}-*'
        else:
            path_pattern = f's1?-iw{subswath}-slc-{polarization.lower()}-*'
        datapaths = pattern2paths(path_pattern + '.tiff')
        #print ('datapaths', datapaths)
        metapaths = pattern2paths(path_pattern + '.xml')
        #print ('metapaths', metapaths)
        if calibration:
            noisepaths = pattern2paths('noise-' + path_pattern + '.xml')
            #print ('noisepaths', noisepaths)
            calibpaths = pattern2paths('calibration-' + path_pattern + '.xml')
            #print ('calibpaths', calibpaths)

        datanames = [os.path.splitext(os.path.split(path)[-1])[0] for path in datapaths]
        #print ('datanames', datanames)
        metanames = [os.path.splitext(os.path.split(path)[-1])[0] for path in metapaths]
        #print ('metanames', metanames)
        if calibration:
            noisenames = [os.path.splitext(os.path.split(path)[-1])[0][6:] for path in noisepaths]
            #print ('noisenames', noisenames)
            calibnames = [os.path.splitext(os.path.split(path)[-1])[0][12:] for path in calibpaths]
            #print ('calibnames', calibnames)

        datas = dict(zip(datanames, datapaths))
        metas = dict(zip(metanames, metapaths))
        if calibration:
            noises = dict(zip(noisenames, noisepaths))
            calibs = dict(zip(calibnames, calibpaths))

        # define the same order when and only when the names are the same
        datanames = sorted(datanames)
        metanames = sorted(metanames)
        assert datanames == metanames, 'Found inconsistent set of .tiff and .xml files'
        # reorder paths using the same order
        datapaths = [datas[name] for name in datanames]
        metapaths = [metas[name] for name in metanames]
        if calibration:
            noisenames = sorted(noisenames)
            calibnames = sorted(calibnames)
            assert datanames == noisenames, 'Found inconsistent set of .xml files'
            assert noisenames == calibnames, 'Found inconsistent set of calibration .xml files'
            noisepaths = [noises[name] for name in noisenames]
            calibpaths = [calibs[name] for name in calibnames]

        # points to datadir and extensions tiff, xml
        #print ('filenames', filenames)
        dts = [text2date(name.split('-')[4],False) for name in datanames]
        #print ('filedatetimes', dts)

        ds = [dt.date() for dt in dts]
        #print ('filedates', ds)

        df = pd.DataFrame({
                            'date':[str(d) for d in ds],
                            'datetime': dts,
                            'datapath': datapaths,
                            'metapath': metapaths,
                            'noisepath': noisepaths if calibration else len(dts)*[None],
                            'calibpath': calibpaths if calibration else len(dts)*[None]
                           })
        #print ('df', df)
        assert len(df), f'Scenes not found'

        # filter mission and always ignore approximate RESORB orbits to download precise POEORB when possible
        if mission is not None:
            orbit_path_pattern = f'{mission.upper()}_OPER_AUX_???ORB_OPOD_*.EOF'
        else:
            orbit_path_pattern = 'S1?_OPER_AUX_???ORB_OPOD_*.EOF'
        orbitpaths = pattern2paths(orbit_path_pattern)
        #print ('orbitpaths', orbitpaths)
        orbitnames = [os.path.splitext(os.path.split(path)[-1])[0] for path in orbitpaths]
        if orbitpaths:
            orbit_dates = [(text2date(name.split('_')[-2]), text2date(name.split('_')[-1])) for name in orbitnames]
            orbits = dict(zip(orbit_dates, orbitpaths))
            #print ('orbits', orbits)
            # look for as precise (from date-1 day to date+1 day) as restituted orbits (from date to date or date-1 to date)
            orbits = [orbits.get((date-oneday, date+oneday)) or
                      orbits.get((date-oneday, date)) or
                      orbits.get((date, date)) for date in ds]
            #print ('fileorbits', fileorbits)
            df['orbitpath'] = orbits
        else:
            df['orbitpath'] = None

        # add some calculated properties
        df['subswath'] = [int(filename.split('-')[1][-1]) for filename in datanames]
        df['mission'] = [filename.split('-')[0].upper() for filename in datanames]
        df['polarization'] = [filename.split('-')[3].upper() for filename in datanames]
    
        # read approximate locations
        #geolocs = [shapely.geometry.MultiPoint(self.geoloc(path).geometry).minimum_rotated_rectangle for path in metapaths]
        #print ('geolocs', geolocs)
        #df = gpd.GeoDataFrame(df, geometry=geolocs)

        bursts = [S1.geoloc2bursts(path) for path in metapaths]
        df = gpd.GeoDataFrame(df, geometry=bursts)

        # define orbit directions
        orbits = [S1.read_annotation(path)['product']['generalAnnotation']['productInformation']['pass'][:1] for path in metapaths]
        df['orbit'] = orbits
        # filter orbits
        if orbit is not None:
            df = df[df.orbit == orbit]
        #print ('df', df)
        assert len(df), f'Scenes not found for the defined orbit {orbit}'

        # see https://github.com/mobigroup/gmtsar/issues/8
        df = df.sort_values(by=['date', 'subswath']).set_index('date')\
            [['datetime','orbit','mission','polarization','subswath','datapath','metapath','noisepath','calibpath','orbitpath','geometry']]

        # Validate the DataFrame to check for any issues or inconsistencies.
        # we can't merge together scenes from different missions
        missions = df.groupby('date')['mission'].unique().values
        missions = [len(mission) for mission in missions if len(mission)>1]
        if not len(missions) == 0:
            raise ValueError('ERROR: Found multiple scenes for a single date from different missions')
        # note: df.unique() returns unsorted values so it would be 21 instead of expected 12
        subswaths = int(''.join(map(str,np.unique(df.subswath))))
        if not int(subswaths) in [1, 2, 3, 12, 23, 123]:
            raise ValueError(f'ERROR: Subswhats list {subswaths} incorrect. Allowed a single or sequential subswath numbers 1, 2, 3, 12, 23, 123')
        if not len(df.orbit.unique()) <= 1:
            raise ValueError('ERROR: Only single orbit processing supported. Use any one ascending or descending')
        if not len(df.index.unique()) >= 2:
            raise ValueError('ERROR: Two or more scenes required')
        daily_scenes = df.groupby(['date', 'subswath'])['datetime'].count().values.max()
        if daily_scenes > 1:
            print ('NOTE: Found multiple scenes for a single day, use function Stack.reframe() to stitch the scenes')

        return df

    @staticmethod
    def geoloc2bursts(metapath):
        """
        Read approximate bursts locations
        """
        from shapely.geometry import LineString, Polygon, MultiPolygon
        df = S1.get_geoloc(S1.read_annotation(metapath))
        # this code line works for a single scene
        #lines = df.groupby('line')['geometry'].apply(lambda x: LineString(x.tolist()))
        # more complex code is required for stitched scenes processing with repeating 'line' series
        df['line_change'] = df['line'].diff().ne(0).cumsum()
        # single-point lines possible for stitched scenes
        grouped_lines = df.groupby('line_change')['geometry'].apply(lambda x: LineString(x.tolist()) if len(x) > 1 else None)
        lines = grouped_lines.reset_index(drop=True)
        #bursts = [Polygon([*line1.coords, *line2.coords[::-1]]) for line1, line2 in zip(lines[:-1], lines[1:])]
        # to ignore None for single-point lines
        bursts = []
        prev_line = None
        for line in lines:
            if line is not None and prev_line is not None:
                bursts.append(Polygon([*prev_line.coords, *line.coords[::-1]]))
            prev_line = line
        return MultiPolygon(bursts)

    @staticmethod
    def read_annotation(filename):
        """
        Return the XML scene annotation as a dictionary.

        Parameters
        ----------
        filename : str
            The filename of the XML scene annotation.

        Returns
        -------
        dict
            The XML scene annotation as a dictionary.
        """
        import xmltodict

        with open(filename) as fd:
            # fix wrong XML tags to process cropped scenes
            # GMTSAR assemble_tops.c produces malformed xml
            # https://github.com/gmtsar/gmtsar/issues/354
            doc = xmltodict.parse(fd.read().replace('/></','></'))
        return doc

    @staticmethod
    def get_geoloc(annotation):
        """
        Build approximate scene polygons using Ground Control Points (GCPs) from XML scene annotation.

        Parameters
        ----------
        filename : str, optional
            The filename of the XML scene annotation. If None, print a note and return an empty DataFrame. Default is None.

        Returns
        -------
        geopandas.GeoDataFrame
            A GeoDataFrame containing the approximate scene polygons.

        annotation = S1.read_annotation(filename)
        S1.get_geoloc(annotation)
        """
        import numpy as np
        import pandas as pd
        import geopandas as gpd
        import os

        geoloc = annotation['product']['geolocationGrid']['geolocationGridPointList']
        # check data consistency
        assert int(geoloc['@count']) == len(geoloc['geolocationGridPoint'])
    
        gcps = pd.DataFrame(geoloc['geolocationGridPoint'])
        # convert to numeric values excluding azimuthTime & slantRangeTime
        for column in gcps.columns[2:]:
            gcps[column] = pd.to_numeric(gcps[column])

        # return approximate location as set of GCP
        return gpd.GeoDataFrame(gcps, geometry=gpd.points_from_xy(x=gcps.longitude, y=gcps.latitude))
