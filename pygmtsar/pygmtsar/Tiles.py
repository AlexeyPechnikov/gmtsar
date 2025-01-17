# ----------------------------------------------------------------------------
# PyGMTSAR
# 
# This file is part of the PyGMTSAR project: https://github.com/mobigroup/gmtsar
# 
# Copyright (c) 2024, Alexey Pechnikov
# 
# Licensed under the BSD 3-Clause License (see LICENSE for details)
# ----------------------------------------------------------------------------
from .datagrid import datagrid
from .tqdm_joblib import tqdm_joblib

class Tiles(datagrid, tqdm_joblib):

    http_timeout = 30
#     http_chunk_size = 8*1024**2
        # Define typical browser headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.example.com',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'Upgrade-Insecure-Requests': '1',
        'DNT': '1',
    }
    
    def _download_tile(self, base_url, path_id, tile_id, file_id, archive, filetype, product, lon, lat, debug=False):
        """
        Download gzipped NetCDF tiles.
        """
        import rioxarray as rio
        import xarray as xr
        import requests
        import os
        import tempfile
        import zipfile
        import gzip
        import io

        product1 = int(product[0])
        if product in ['1s', '01s']:
            resolution = '30'
        elif product in ['3s', '03s']:
            resolution = '90'
        else:
            resolution = ''
        # substitute all the allowed parameters
        params = {
            'product': product,
            'lat': lat,
            'lon': lon,
            'product1': product1,
            'resolution': resolution,
            # 1 degree grid
            'SN2':    f'{"S" if lat<0 else "N"}{abs(lat):02}',
            'SN3':    f'{"S" if lat<0 else "N"}{abs(lat):03}',
            'WE3':    f'{"W" if lon<0 else "E"}{abs(lon):03}',
            # standalone 5 degree grid (SRTM and GLO DEM)
            'SN2x5': f'{"S" if lat<0 else "N"}{abs(lat) - (abs(lat) % 5):02}',
            'SN3x5': f'{"S" if lat<0 else "N"}{abs(lat) - (abs(lat) % 5):03}',
            'WE3x5': f'{"W" if lon<0 else "E"}{abs(lon) - (abs(lon) % 5):03}',
            # 5 degree alternative grid when negative grid cells aligning differ (ALOS DEM)
            'SN2x5alt': f'{"S" if lat < 0 else "N"}{(abs(lat) // 5 * 5 if lat >= 0 else (abs(lat) // 5 + 1) * 5):02}',
            'SN3x5alt': f'{"S" if lat < 0 else "N"}{(abs(lat) // 5 * 5 if lat >= 0 else (abs(lat) // 5 + 1) * 5):03}',
            'WE3x5alt': f'{"W" if lon < 0 else "E"}{(abs(lon) // 5 * 5 if lon >= 0 else (abs(lon) // 5 + 1) * 5):03}'
        }
        if debug:
            print ('DEBUG _download_tile: params', params)
        url = base_url.format(**params)
        path = path_id.format(**params)
        file = file_id.format(**params) if file_id is not None else None
        tile = tile_id.format(**params)
        tile_url = f'{url}/{path}/{tile}'
        if archive is not None and len(archive)>0:
            # remove .gz or other archive extension
            ext_len = len(archive) + 1
            tile_filename = os.path.join(tempfile.gettempdir(), tile[:-ext_len])
        else:
            tile_filename = os.path.join(tempfile.gettempdir(), tile)
        if debug:
            print ('DEBUG _download_tile: file', file)
            print ('DEBUG _download_tile: tile_url', tile_url)
            print ('DEBUG _download_tile: tile_filename', tile_filename)
        try:
            #if archive is not None and len(archive)>0:
#                 with requests.get(tile_url, stream=True, headers=self.headers, timeout=self.http_timeout) as response:
#                     response.raise_for_status()
#                     # Stream the content under the context of gzip decompression
#                     with gzip.GzipFile(fileobj=response.raw) as gz:
#                         with open(tile_filename, 'wb') as f:
#                             while True:
#                                 chunk = gz.read(chunk_size)
#                                 if not chunk:
#                                     break
#                                 f.write(chunk)

#                 with requests.get(tile_url, stream=True, headers=self.headers, timeout=self.http_timeout) as response:
#                     response.raise_for_status()
#                     # Stream the content under the context of gzip decompression
#                     with gzip.GzipFile(fileobj=response.raw) as gz:
#                         with open(tile_filename, 'wb') as f:
#                             f.write(gz.read())
            if archive is not None and archive == 'zip':
                with requests.get(tile_url, headers=self.headers, timeout=self.http_timeout) as response:
                    response.raise_for_status()
                    compressed_content = io.BytesIO(response.content)
                    with zipfile.ZipFile(compressed_content, 'r') as zip:
                        zip_files = zip.namelist()
                        if debug:
                            print ('DEBUG _download_tile: zip files', zip_files)
                        if len(zip_files) == 0:
                            raise Exception('ERROR: Downloaded file is empty zip archive.')
                        if file not in zip_files:
                            raise Exception(f'ERROR: Downloaded zip archive does not includes file {file}')
                        # extract specific file content
                        with open(tile_filename, 'wb') as f:
                            f.write(zip.read(file))
            elif archive is not None and archive == 'gz':
                with requests.get(tile_url, headers=self.headers, timeout=self.http_timeout) as response:
                    response.raise_for_status()
                    # Since we're not streaming, response.content contains the entire gzip-compressed content
                    # We'll wrap the compressed content in BytesIO so it behaves like a file object
                    compressed_content = io.BytesIO(response.content)
                    # Decompress and write the content
                    with gzip.GzipFile(fileobj=compressed_content) as gz:
                        with open(tile_filename, 'wb') as f:
                            f.write(gz.read())
            else:
#                 with requests.get(tile_url, stream=True, headers=self.headers, timeout=self.http_timeout) as response:
#                     response.raise_for_status()
#                     with open(tile_filename, 'wb') as f:
#                         for chunk in response.iter_content(chunk_size=self.http_chunk_size):
#                             f.write(chunk)
                with requests.get(tile_url, headers=self.headers, timeout=self.http_timeout) as response:
                    response.raise_for_status()
                    with open(tile_filename, 'wb') as f:
                        f.write(response.content)
            if filetype == 'netcdf':
                with xr.open_dataarray(tile_filename) as ds:
                    tile = ds.load()
                tile.attrs = {}
                for coord in tile.coords:
                    tile.coords[coord].attrs = {}
            elif filetype == 'geotif':
                with rio.open_rasterio(tile_filename) as raster:
                    tile = raster\
                        .squeeze(drop=True)\
                        .rename({'y': 'lat', 'x': 'lon'})\
                        .drop_vars('spatial_ref')\
                        .load()
                if tile.lat.diff('lat')[0].item() < 0:
                    tile = tile.reindex(lat=tile.lat[::-1])
            else:
                raise Exception(f'ERROR:: unknown tiles file type {filetype}. Expected "netcdf" or "geotif".')
        except requests.exceptions.RequestException as e:
            # offshore tiles are missed by design
            print(f'Request error for {tile_id}: {e}')
            tile = None
        except Exception as e:
            print(e)
            raise
        finally:
            if os.path.exists(tile_filename):
                os.remove(tile_filename)
        return tile

    def download(self, base_url, path_id, tile_id, archive, filetype,
                  geometry, file_id=None, filename=None, product='1s',
                  n_jobs=4, joblib_backend='loky', skip_exist=True, debug=False):
        """
        Download and merge gzipped NetCDF tiles from a defined access point.
        """
        import xarray as xr
        import numpy as np
        from tqdm.auto import tqdm
        import joblib
        import os

        assert product in ['1s', '3s'], f'ERROR: product name is invalid: {product}. Expected names are "1s", "3s".'

        if filename is not None and os.path.exists(filename) and skip_exist:
            print ('NOTE: Target file exists, return it. Use "skip_exist=False" or omit the filename to allow new downloading.')
            return xr.open_dataarray(filename, engine=self.netcdf_engine, chunks=self.chunksize)

        bounds = self.get_bounds(geometry)

        # it produces 4 tiles for cases like (39.5, 39.5, 40.0, 40.0)
        #left, right = int(np.floor(lon_start)), int(np.floor(lon_end))
        #bottom, top = int(np.floor(lat_start)), int(np.floor(lat_end))
        # enhancement to produce a single tile for cases like (39.5, 39.5, 40.0, 40.0)
        lon_start, lat_start, lon_end, lat_end = bounds
        left = np.floor(min(lon_start, lon_end))
        right = np.ceil(max(lon_start, lon_end)) - 1
        bottom = np.floor(min(lat_start, lat_end))
        top = np.ceil(max(lat_start, lat_end)) - 1
        left, right = int(left), int(right)
        bottom, top = int(bottom), int(top)
        #print ('left, right', left, right, 'bottom, top', bottom, top)

        if n_jobs is None or debug == True:
            print ('Note: sequential joblib processing is applied when "n_jobs" is None or "debug" is True.')
            joblib_backend = 'sequential'

        with self.tqdm_joblib(tqdm(desc=f'Tiles Parallel Downloading', total=(right-left+1)*(top-bottom+1))) as progress_bar:
            tile_xarrays = joblib.Parallel(n_jobs=n_jobs, backend=joblib_backend)(joblib.delayed(self._download_tile)\
                                (base_url, path_id, tile_id, file_id, archive, filetype, product, x, y, debug)\
                                for x in range(left, right + 1) for y in range(bottom, top + 1))

        tile_xarrays = [tile for tile in tile_xarrays if tile is not None]
        if len(tile_xarrays) == 0:
            return
        da = xr.combine_by_coords(tile_xarrays)
        # drop duplicate indices for SRTM DEM when neighboring tiles share the same edge coordinates
        da = da.sel(lat=~da.indexes['lat'].duplicated(), lon=~da.indexes['lon'].duplicated())
        
        if isinstance(da, xr.Dataset):
            da = da[list(da.data_vars)[0]]
        # crop geometry extent        
        da = da.sel(lat=slice(bounds[1], bounds[3]), lon=slice(bounds[0], bounds[2]))

        if filename is not None:
            if os.path.exists(filename):
                os.remove(filename)
            encoding = {'z': self._compression(da.shape)}
            da.rename('z').to_netcdf(filename, encoding=encoding, engine=self.netcdf_engine)
        return da

    def download_landmask(self, geometry, filename=None, product='1s', skip_exist=True, n_jobs=8, debug=False):
        """
        Download and merge gzipped NetCDF tiles for land mask.

        from pygmtsar import Tiles
        landmask = Tiles().download_landmask(AOI)
        landmask.plot.imshow()

        Tiles().download_landmask(S1.scan_slc(DATADIR), 'landmask.nc')
        """
        return self.download(
                         base_url       = 'https://gmtlandmask.pechnikov.workers.dev/{product}',
                         #base_url       = 'https://alexeypechnikov.github.io/gmtlandmask/{product}',
                         path_id        = '{SN2}',
                         tile_id        = '{SN2}{WE3}.nc.gz',
                         archive        = 'gz',
                         filetype       = 'netcdf',
                         geometry       = geometry,
                         filename       = filename,
                         product        = product,
                         n_jobs         = n_jobs,
                         joblib_backend = 'loky',
                         skip_exist     = skip_exist,
                         debug          = debug)

    # https://copernicus-dem-90m.s3.eu-central-1.amazonaws.com
    # https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N38_00_E038_00_DEM/Copernicus_DSM_COG_10_N38_00_E038_00_DEM.tif
    def download_dem_glo(self, geometry, filename=None, product='1s', skip_exist=True, n_jobs=8, debug=False):
        """
        Download Copernicus GLO-30/GLO-90 Digital Elevation Model tiles from open AWS storage.

        from pygmtsar import Tiles
        dem = Tiles().download_dem_glo(AOI)
        dem.plot.imshow()

        Tiles().download_dem_glo(S1.scan_slc(DATADIR), 'dem_glo.nc')
        """
        assert product in ['1s', '3s'], f'ERROR: product name is invalid: {product} for Copernicus GLO DEM. Expected names are "1s", "3s".'
        return self.download(
                         #base_url       = 'https://copernicus-dem-{resolution}m.s3.amazonaws.com',
                         base_url       = 'https://copernicusdem{product1}s.pechnikov.workers.dev',
                         path_id        = 'Copernicus_DSM_COG_{product1}0_{SN2}_00_{WE3}_00_DEM',
                         tile_id        = 'Copernicus_DSM_COG_{product1}0_{SN2}_00_{WE3}_00_DEM.tif',
                         archive        = None,
                         filetype       = 'geotif',
                         geometry       = geometry,
                         filename       = filename,
                         product        = product,
                         skip_exist     = skip_exist,
                         n_jobs         = n_jobs,
                         debug          = debug)

    # aws s3 ls --no-sign-request s3://elevation-tiles-prod/skadi/
    # https://s3.amazonaws.com/elevation-tiles-prod/skadi/N20/N20E000.hgt.gz
    def download_dem_srtm(self, geometry, filename=None, product='1s', skip_exist=True, n_jobs=8, debug=False):
        """
        Download NASA SRTM Digital Elevation Model tiles from open AWS storage.

        from pygmtsar import Tiles
        dem = Tiles().download_dem_srtm(AOI)
        dem.plot.imshow()

        Tiles().download_dem_srtm(S1.scan_slc(DATADIR), 'dem_srtm.nc')
        """
        assert product in ['1s'], f'ERROR: only product="1s" is supported for NASA SRTM DEM.'
        return self.download(
                         #base_url       = 'https://s3.amazonaws.com/elevation-tiles-prod/skadi',
                         base_url       = 'https://srtmdem1s.pechnikov.workers.dev',
                         path_id        = '{SN2}',
                         tile_id        = '{SN2}{WE3}.hgt.gz',
                         archive        = 'gz',
                         filetype       = 'geotif',
                         geometry       = geometry,
                         filename       = filename,
                         product        = product,
                         skip_exist     = skip_exist,
                         n_jobs         = n_jobs,
                         debug          = debug)

    # Define new method to download ALOS DEM
    # https://www.eorc.jaxa.jp/ALOS/aw3d30/data/release_v2404/N025E040/N027E042.zip N027E042/ALPSMLC30_N027E042_DSM.tif
    def download_dem_alos(self, geometry, filename=None, product='1s', skip_exist=True, n_jobs=8, debug=False):
            """
            Download JAXA ALOS Digital Elevation Model tiles from open JAXA storage.
    
            from pygmtsar import Tiles
            Tiles().download_dem_alos(AOI, filename=DEM).plot.imshow(cmap='terrain')
            """
            assert product in ['1s'], f'ERROR: only product="1s" is supported for JAXA ALOS DEM.'
            return self.download(
                             #base_url       = 'https://www.eorc.jaxa.jp/ALOS/aw3d30/data/release_v2404/',
                             base_url       = 'https://alosdem1s.pechnikov.workers.dev',
                             path_id        = '{SN3x5alt}{WE3x5alt}',
                             tile_id        = '{SN3}{WE3}.zip',
                             file_id        = '{SN3}{WE3}/ALPSMLC30_{SN3}{WE3}_DSM.tif',
                             archive        = 'zip',
                             filetype       = 'geotif',
                             geometry       = geometry,
                             filename       = filename,
                             product        = product,
                             skip_exist     = skip_exist,
                             n_jobs         = n_jobs,
                             debug          = debug)

    def download_dem(self, geometry, filename=None, product='1s', provider='GLO', skip_exist=True, n_jobs=8, debug=False):
        """
        Downloads Copernicus or SRTM Digital Elevation Model (DEM) at 30m or 90m resolution.

        Parameters
        ----------
        geometry : object
            The Shapely geometry or GeoPandas object or Xarray object for which to download the DEM.
        filename : str or None, optional
            The name of the file to save the downloaded DEM. If None, a default name will be generated. Default is None.
        product : str, optional
            The resolution of the DEM. Valid options are '1s' (for 30m) and '3s' (for 90m). Default is '1s'.
        provider : str, optional
            The provider of the DEM. Valid options are 'GLO' (for Copernicus Global Land Service), 'SRTM', and 'ALOS'. Default is 'GLO'.
        skip_exist : bool, optional
            If True, skips the download if the file already exists. Default is True.
        n_jobs : int, optional
            The number of concurrent download jobs. Default is 8.
        debug : bool, optional
            If True, prints debugging information. Default is False.

        Returns
        -------
        str
            The ID of the downloaded DEM file.

        Raises
        ------
        AssertionError
            If an invalid provider or product is specified.

        Examples
        --------
        Tiles().download_dem(AOI, filename='dem.tif', product='1s', provider='GLO', n_jobs=4, skip_exist=True, debug=True)
        """
        kwargs = dict(geometry   = geometry,
                      filename   = filename,
                      product    = product,
                      skip_exist = skip_exist,
                      n_jobs     = n_jobs,
                      debug=debug)
        assert provider in ['GLO', 'SRTM', 'ALOS'], f'ERROR: provider name is invalid: {provider}. Expected names are "GLO", "SRTM", "ALOS".'
        if provider == 'SRTM':
            return self.download_dem_srtm(**kwargs)
        elif provider == 'GLO':
            return self.download_dem_glo(**kwargs)
        elif provider == 'ALOS':
            return self.download_dem_alos(**kwargs)
