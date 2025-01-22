# ----------------------------------------------------------------------------
# PyGMTSAR
#.
# This file is part of the PyGMTSAR project: https://github.com/mobigroup/gmtsar
#.
# Copyright (c) 2023, Alexey Pechnikov
#.
# Licensed under the BSD 3-Clause License (see LICENSE for details)
# ----------------------------------------------------------------------------
from .datagrid import datagrid
from .tqdm_dask import tqdm_dask

class IO(datagrid):

    # processing directory
    basedir = '.'

    def _glob_re(self, pathname):
        import os
        import re
        filenames = filter(re.compile(pathname).match, os.listdir(self.basedir))
        return sorted([os.path.join(self.basedir, filename) for filename in filenames])

    def dump(self, to_path=None):
        """
        Dump Stack object state to a pickle file (stack.pickle in the processing directory by default).

        Parameters
        ----------
        to_path : str, optional
            Path to the output dump file. If not provided, the default dump file in the processing directory is used.

        Returns
        -------
        None

        Examples
        --------
        Dump the current state to the default dump file in the processing directory:
        stack.dump()

        Notes
        -----
        This method serializes the state of the Stack object and saves it to a pickle file. The pickle file can be used to
        restore the Stack object with its processed data and configuration. By default, the dump file is named "stack.pickle"
        and is saved in the processing directory. An alternative file path can be provided using the `to_path` parameter.
        """
        import pickle
        import os

        if to_path is None:
            stack_pickle = os.path.join(self.basedir, 'stack.pickle')
        else:
            if os.path.isdir(to_path):
                stack_pickle = os.path.join(to_path, 'stack.pickle')
            else:
                stack_pickle = to_path
    
        print (f'NOTE: save state to file {stack_pickle}')
        pickle.dump(self, open(stack_pickle, 'wb'))

        return

    @staticmethod
    def restore(from_path):
        """
        Restore Stack object state from a pickle file (stack.pickle in the processing directory by default).

        Parameters
        ----------
        from_path : str
            Path to the input dump file.

        Returns
        -------
        Stack
            The restored Stack object.

        Examples
        --------
        Restore the current state from the default dump file in the processing directory:
        Stack.restore()

        Notes
        -----
        This static method restores the state of an Stack object from a pickle file. The pickle file should contain the
        serialized state of the Stack object, including its processed data and configuration. By default, the method assumes
        the input file is named "stack.pickle" and is located in the processing directory. An alternative file path can be
        provided using the `from_path` parameter. The method returns the restored Stack object.
        """
        import pickle
        import os

        if os.path.isdir(from_path):
            stack_pickle = os.path.join(from_path, 'stack.pickle')
        else:
            stack_pickle = from_path

        print (f'NOTE: load state from file {stack_pickle}')
        with open(stack_pickle, 'rb') as f:
            return pickle.load(f)

    def backup(self, backup_dir, copy=False, debug=False):
        """
        Backup framed Stack scenes, orbits, DEM, and landmask files to build a minimal reproducible dataset.

        Parameters
        ----------
        backup_dir : str
            The backup directory where the files will be copied.
        copy : bool, optional
            Flag indicating whether to make a copy of scene and orbit files and remove the originals in the work directory.
            If False, the files will be moved to the backup directory. Default is False.
        debug : bool, optional
            Flag indicating whether to print debug information. Default is False.

        Returns
        -------
        None

        Examples
        --------
        Backup the files to the specified directory:
        stack.backup('backup')

        Open the backup for the reproducible run by defining it as a new data directory:
        stack = Stack('backup', 'backup/DEM_WGS84.nc', 'raw')

        Notes
        -----
        This method backs up the framed Stack scenes, orbits, DEM, and landmask files to a specified backup directory.
        It provides a way to create a minimal reproducible dataset by preserving the necessary files for processing.
        The method creates the backup directory if it does not exist. By default, the method moves the scene and orbit files
        to the backup directory, effectively removing them from the work directory. The DEM and landmask files are always
        copied to the backup directory. If the `copy` parameter is set to True, the scene and orbit files will be copied
        instead of moved. Use caution when setting `copy` to True as it can result in duplicated files and consume
        additional storage space. The method also updates the Stack object's dataframe to mark the removed files as empty.
        """
        import os
        import shutil

        os.makedirs(backup_dir, exist_ok=True)

        # save the geometry
        filename = os.path.join(backup_dir, 'stack.geojson')
        self.df[['datetime', 'orbit','mission','polarization', 'subswath','geometry']].to_file(filename, driver='GeoJSON')

        # this optional file is dumped state, copy it if exists
        # auto-generated file can't be a symlink but user-defined symlink target should be copied
        filename = os.path.join(self.basedir, 'stack.pickle')
        if os.path.exists(filename):
            if debug:
                print ('DEBUG: copy', filename, backup_dir)
            shutil.copy2(filename, backup_dir, follow_symlinks=True)

        # these files required to continue the processing, do not remove and copy only
        filenames = [self.dem_filename, self.landmask_filename]
        for filename in filenames:
            # DEM and landmask can be not defined
            if filename is None:
                continue
            if debug:
                print ('DEBUG: copy', filename, backup_dir)
            shutil.copy2(filename, backup_dir, follow_symlinks=True)

        # these files are large and are not required to continue the processing
        filenames = []
        for record in self.df.itertuples():
            for filename in [record.datapath, record.metapath, record.orbitpath]:
                filenames += filename if isinstance(filename, list) else [filename]
        for filename in filenames:
            # orbit files can be not defined
            if filename is None:
                continue
            # copy and delete the original later to prevent cross-device links issues
            if debug:
                print ('DEBUG: copy', filename, backup_dir)
            shutil.copy2(filename, backup_dir, follow_symlinks=True)
            if not copy and self.basedir == os.path.dirname(filename):
                # when copy is not needed then delete files in work directory only
                if debug:
                    print ('DEBUG: remove', filename)
                os.remove(filename)

        if not copy:
            # mark as empty all the removed files
            for col in ['datapath','metapath','orbitpath']:
                self.df[col] = None
        return

    def get_filename(self, name, add_subswath=False):
        import os

        if add_subswath:
            subswath = self.get_subswath()
            prefix = f'F{subswath}_'
        else:
            prefix = ''

        filename = os.path.join(self.basedir, f'{prefix}{name}.grd')
        return filename

    def get_filenames(self, pairs, name, add_subswath=False):
        """
        Get the filenames of the data grids. The filenames are determined by the subswath, pairs, and name parameters.

        Parameters
        ----------
        subswath : int or None
            The subswath number. If None, the function will determine it based on the dataset.
        pairs : np.ndarray or pd.DataFrame or None
            An array or DataFrame of pairs. If None, the function will open a single grid or a set of subswath grids.
        name : str
            The name of the grid to be opened.
        add_subswath : bool, optional
            Whether to add subswath to the prefix of the filename. Default is True.

        Returns
        -------
        str or list of str
            The filename or a list of filenames of the grids.
        """
        import pandas as pd
        import numpy as np
        import os

        if add_subswath:
            subswath = self.get_subswath()
            prefix = f'F{subswath}_'
        else:
            prefix = ''

        if isinstance(pairs, pd.DataFrame):
            # convert to standalone DataFrame first
            pairs = self.get_pairs(pairs)[['ref', 'rep']].astype(str).values
        else:
            pairs = np.asarray(pairs)

        filenames = []
        if len(pairs.shape) == 1:
            # read all the grids from files
            for date in sorted(pairs):
                filename = os.path.join(self.basedir, f'{prefix}{name}_{date}.grd'.replace('-',''))
                filenames.append(filename)
        elif len(pairs.shape) == 2:
            # read all the grids from files
            for pair in pairs:
                filename = os.path.join(self.basedir, f'{prefix}{name}_{pair[0]}_{pair[1]}.grd'.replace('-',''))
                filenames.append(filename)
        return filenames

#     # 2.5e-07 is Sentinel-1 scale factor
#     def open_data(self, dates=None, scale=2.5e-07, debug=False):
#         import xarray as xr
#         import pandas as pd
#         import numpy as np
#         import os
# 
#         if debug:
#             print ('DEBUG: open_data: apply scale:', scale)
# 
#         if dates is None:
#             dates = self.df.index.values
#         #print ('dates', dates)
# 
#         filenames = [self.PRM(date).filename[:-4] + '.grd' for date in dates]
#         #print ('filenames', filenames)
#         ds = xr.open_mfdataset(
#             filenames,
#             engine=self.netcdf_engine,
#             chunks=self.chunksize,
#             parallel=True,
#             concat_dim='date',
#             combine='nested'
#         ).assign(date=pd.to_datetime(dates)).rename({'a': 'y', 'r': 'x'})
#         if scale is None:
#             # there is no complex int16 datatype, so return two variables for real and imag parts
#             return ds
#         # scale and return as complex values
#         ds_scaled = (scale*(ds.re.astype(np.float32) + 1j*ds.im.astype(np.float32))).assign_attrs(ds.attrs).rename('data')
#         del ds
#         # zero in np.int16 type means NODATA
#         return ds_scaled.where(ds_scaled != 0)

    # 2.5e-07 is Sentinel-1 scale factor
    # use original PRM files to get binary subswath file locations
    def open_data(self, dates=None, subswath=None, scale=2.5e-07, debug=False):
        import xarray as xr
        import pandas as pd
        import numpy as np
        from scipy import constants
        import os

        if debug:
            print ('DEBUG: open_data: apply scale:', scale)

        if dates is None:
            #dates = self.df.index.values
            dates = np.unique(self.df.index.values)
        #print ('dates', dates)

        subswaths = self.get_subswaths()
        if not isinstance(subswaths, (str, int)):
            subswaths = ''.join(map(str, subswaths))
        #print ('subswaths', subswaths)

        #offsets = {'bottoms': bottoms, 'lefts': lefts, 'rights': rights, 'bottom': minh, 'extent': [maxy, maxx], 'ylims': ylims, 'xlims': xlims}
        offsets = self.prm_offsets(debug=debug)
        #print ('offsets', offsets)

        if len(subswaths) == 1:
            # stack single subswath
            stack = []
            shape = offsets['extent']
            for date in dates:
                prm = self.PRM(date, subswath=int(subswaths))
                # disable scaling
                slc = prm.read_SLC_int(scale=scale, shape=shape)
                stack.append(slc.assign_coords(date=date))
                if shape is None:
                    shape = (slc.y.size, slc.x.size)
                del slc, prm
        else:
            maxy, maxx = offsets['extent']
            minh = offsets['bottom']
    
            # merge subswaths
            stack = []
            for date in dates:
                slcs = []
                prms = []

                # for single subswath accumulate offset in scene coordinates
                offsetx = 0
                for sw, bottom, left, right, ylim, xlim in zip(subswaths, 
                        offsets['bottoms'], offsets['lefts'], offsets['rights'], offsets['ylims'], offsets['xlims']):
                    #print (date, subswath)
                    if subswath is not None and not str(subswath) == sw:
                        offsetx += right - left
                        continue
                    prm = self.PRM(date, subswath=int(sw))
                    # disable scaling
                    slc = prm.read_SLC_int(scale=scale, shape=(ylim, xlim))
                    slc = slc.isel(x=slice(left if subswath is None else None, right if subswath is None else None))\
                             .assign_coords(y=slc.y + bottom)
                    if subswath is not None:
                        slc = slc.assign_coords(x=slc.x + offsetx - left)
                    slcs.append(slc)
                    prms.append(prm)

                if subswath is None:
                    # check and merge SLCs, use zero fill for np.int16 datatype
                    slc = xr.concat(slcs, dim='x', fill_value=0).assign_coords(x=0.5 + np.arange(maxx))
    
                    if debug:
                        print ('assert slc.y.size == maxy', slc.y.size, maxy)
                    assert slc.y.size == maxy, 'Incorrect output grid azimuth dimension size'
                    if debug:
                        print ('assert slc.x.size == maxx', slc.x.size, maxx)
                    assert slc.x.size == maxx, 'Incorrect output grid range dimension sizes'
                del slcs

                stack.append(slc.assign_coords(date=date))
                del slc

        # DEM extent in radar coordinates, merged reference PRM required
        #print ('minx, miny, maxx, maxy', minx, miny, maxx, maxy)
        extent_ra = np.round(self.get_extent_ra().bounds).astype(int)
        #print ('extent_ra', extent_ra)
        # minx, miny, maxx, maxy = extent_ra
        ds = xr.concat(stack, dim='date').assign(date=pd.to_datetime(dates))\
            .sel(y=slice(extent_ra[1], extent_ra[3]), x=slice(extent_ra[0], extent_ra[2])) \
            .chunk({'y': self.chunksize, 'x': self.chunksize})
        del stack

        if scale is None:
            # there is no complex int16 datatype, so return two variables for real and imag parts
            return ds
        # scale and return as complex values
        ds_complex = (ds.re.astype(np.float32) + 1j*ds.im.astype(np.float32))
        del ds
        # zero in np.int16 type means NODATA
        return ds_complex.where(ds_complex != 0).rename('data')

#     def open_geotif(self, dates=None, subswath=None, intensity=False, chunksize=None):
#         """
#         tiffs = stack.open_data_geotif(['2022-06-16', '2022-06-28'], intensity=True)
#         """
#         import xarray as xr
#         import rioxarray as rio
#         import pandas as pd
#         import numpy as np
#         # from GMTSAR code
#         DFACT = 2.5e-07
#     
#         if chunksize is None:
#             chunksize = self.chunksize
# 
#         if subswath is None:
#             subswaths = self.get_subswaths()
#         else:
#             subswaths = [subswath]
# 
#         stack = []
#         for swath in self.get_subswaths():
#             if dates is None:
#                 dates = self.df[self.df['subswath']==swath].index.values
#             #print ('dates', dates)
#             tiffs = self.df[(self.df['subswath']==swath)&(self.df.index.isin(dates))].datapath.values
#             tiffs = [rio.open_rasterio(tif, chunks=chunksize)[0] for tif in tiffs]
#             # build stack
#             tiffs = xr.concat(tiffs, dim='date')
#             tiffs['date'] = pd.to_datetime(dates)
#             # 2 and 4 multipliers to have the same values as in SLC
#             if intensity:
#                 stack.append((2*DFACT*np.abs(tiffs))**2)
#             else:
#                 stack.append(2*DFACT*tiffs)
# 
#         return stacks if subswath is None else stacks[0]

    def open_cube(self, name):
        """
        Opens an xarray 2D/3D Dataset or dataArray from a NetCDF file.

        This function takes the name of the model to be opened, reads the NetCDF file, and re-chunks
        the dataset according to the provided chunksize or the default value from the 'stack' object.
        The 'date' dimension is always chunked with a size of 1.

        Parameters
        ----------
        name : str
            The name of the model file to be opened.

        Returns
        -------
        xarray.Dataset
            Xarray Dataset read from the specified NetCDF file.

        """
        import xarray as xr
        import pandas as pd
        import numpy as np
        import os

        filename = self.get_filename(name)
        assert os.path.exists(filename), f'ERROR: The NetCDF file is missed: {filename}'

        # Workaround: open the dataset without chunking
        data = xr.open_dataset(filename, engine=self.netcdf_engine)
        
        if 'stack' in data.dims:
            if 'y' in data.coords and 'x' in data.coords:
                multi_index_names = ['y', 'x']
            elif 'lat' in data.coords and 'lon' in data.coords:
                multi_index_names = ['lat', 'lon']
            multi_index = pd.MultiIndex.from_arrays([data.y.values, data.x.values], names=multi_index_names)
            data = data.assign_coords(stack=multi_index).set_index({'stack': ['y', 'x']})
            chunksize = self.chunksize1d
        else:
            chunksize = self.chunksize

        # set the proper chunk sizes
        chunks = {dim: 1 if dim in ['pair', 'date'] else chunksize for dim in data.dims}
        data = data.chunk(chunks)

        # attributes are empty when dataarray is prezented as dataset
        # revert dataarray converted to dataset
        data_vars = list(data.data_vars)
        if len(data_vars) == 1 and 'dataarray' in data.attrs:
            assert data.attrs['dataarray'] == data_vars[0]
            data = data[data_vars[0]]

        # convert string dates to dates
        for dim in ['date', 'ref', 'rep']:
            if dim in data.dims:
                data[dim] = pd.to_datetime(data[dim])

        # restore missed coordinates
        for dim in ['y', 'x', 'lat', 'lon']:
            if dim not in data.coords \
                and f'start_{dim}' in data.attrs \
                and f'step_{dim}' in data.attrs \
                and f'stop_{dim}' in data.attrs \
                and f'size_{dim}' in data.attrs:
                start = data.attrs[f'start_{dim}']
                step  = data.attrs[f'step_{dim}']
                stop  = data.attrs[f'stop_{dim}']
                size  = data.attrs[f'size_{dim}']
                coords = np.arange(start, stop+step/2, step)
                assert coords.size == size, 'Restored dimension has invalid size'
                #print (dim, start, step, stop, coords)
                data = data.assign_coords({dim: coords})
                # remove the system attributes
                del data.attrs[f'start_{dim}']
                del data.attrs[f'step_{dim}']
                del data.attrs[f'stop_{dim}']
                del data.attrs[f'size_{dim}']

        return data

    def sync_cube(self, data, name=None, caption='Syncing NetCDF 2D/3D Dataset'):
        import xarray as xr
        if name is None and isinstance(data, xr.DataArray):
            assert data.name is not None, 'Define data name or use "name" argument for the NetCDF filename'
            name = data.name
        elif name is None:
            raise ValueError('Specify name for the output NetCDF file')
        self.save_cube(data, name, caption)
        return self.open_cube(name)

    def save_cube(self, data, name=None, caption='Saving NetCDF 2D/3D Dataset'):
        """
        Save a lazy and not lazy 2D/3D xarray Dataset or DataArray to a NetCDF file.

        The 'date' or 'pair' dimension is always chunked with a size of 1.

        Parameters
        ----------
        data : xarray.Dataset or xarray.DataArray
            The model to be saved.
        name : str
            The text name for the output NetCDF file.
        caption: str
            The text caption for the saving progress bar.

        Returns
        -------
        None

        Examples
        -------
        stack.save_cube(intf90m, 'intf90m')                              # save lazy 3d dataset
        stack.save_cube(intf90m.phase, 'intf90m')                        # save lazy 3d dataarray
        stack.save_cube(intf90m.isel(pair=0), 'intf90m')                 # save lazy 2d dataset
        stack.save_cube(intf90m.isel(pair=0).phase, 'intf90m')           # save lazy 2d dataarray
        stack.save_cube(intf90m.compute(), 'intf90m')                    # save 3d dataset     
        stack.save_cube(intf90m.phase.compute(), 'intf90m')              # save 3d dataarray
        stack.save_cube(intf90m.isel(pair=0).compute(), 'intf90m')       # save 2d dataset
        stack.save_cube(intf90m.isel(pair=0).phase.compute(), 'intf90m') # save 2d dataarray
        """
        import xarray as xr
        import pandas as pd
        import dask
        import os
        import warnings
        # suppress Dask warning "RuntimeWarning: invalid value encountered in divide"
        warnings.filterwarnings('ignore')
        warnings.filterwarnings('ignore', module='dask')
        warnings.filterwarnings('ignore', module='dask.core')
        import logging
        # prevent warnings "RuntimeWarning: All-NaN slice encountered"
        logging.getLogger('distributed.nanny').setLevel(logging.ERROR)
        # disable "distributed.utils_perf - WARNING - full garbage collections ..."
        try:
            from dask.distributed import utils_perf
            utils_perf.disable_gc_diagnosis()
        except ImportError:
            from distributed.gc import disable_gc_diagnosis
            disable_gc_diagnosis()

        if name is None and isinstance(data, xr.DataArray):
            assert data.name is not None, 'Define data name or use "name" argument for the NetCDF filename'
            name = data.name
        elif name is None:
            raise ValueError('Specify name for the output NetCDF file')

        chunksize = None
        if 'stack' in data.dims and isinstance(data.coords['stack'].to_index(), pd.MultiIndex):
            # replace multiindex by sequential numbers 0,1,...
            data = data.reset_index('stack')
            # single-dimensional data compression required
            chunksize = self.netcdf_chunksize1d

        for dim in ['y', 'x', 'lat', 'lon']:
            if dim in data.dims:
                # use attributes to hold grid spacing to prevent xarray Dask saving issues
                data = data.drop(dim, dim=None).assign_attrs({
                    f'start_{dim}': data[dim].values[0],
                    f'step_{dim}': data[dim].diff(dim).values[0],
                    f'stop_{dim}': data[dim].values[-1],
                    f'size_{dim}': data[dim].size
                })

        if isinstance(data, xr.DataArray):
            if data.name is None:
                data = data.rename(name)
            data = data.to_dataset().assign_attrs({'dataarray': data.name})

        is_dask = isinstance(data[list(data.data_vars)[0]].data, dask.array.Array)
        encoding = {varname: self._compression(data[varname].shape, chunksize=chunksize) for varname in data.data_vars}
        #print ('save_cube encoding', encoding)
        #print ('is_dask', is_dask, 'encoding', encoding)

        # save to NetCDF file
        filename = self.get_filename(name)
        if os.path.exists(filename):
            os.remove(filename)
        delayed = data.to_netcdf(filename,
                                 engine=self.netcdf_engine,
                                 encoding=encoding,
                                 compute=not is_dask)
        if is_dask:
            tqdm_dask(result := dask.persist(delayed), desc=caption)
            # cleanup - sometimes writing NetCDF handlers are not closed immediately and block reading access
            del delayed, result
            import gc; gc.collect()

    def delete_cube(self, name):
        import os

        filename = self.get_filename(name)
        #print ('filename', filename)
        if os.path.exists(filename):
            os.remove(filename)

    def sync_stack(self, data, name=None, caption='Saving 2D Stack', queue=None, timeout=300):
        import xarray as xr
        if name is None and isinstance(data, xr.DataArray):
            assert data.name is not None, 'Define data name or use "name" argument for the NetCDF filenames'
            name = data.name
        elif name is None:
            raise ValueError('Specify name for the output NetCDF files')
        self.delete_stack(name)
        self.save_stack(data, name, caption, queue, timeout)
        return self.open_stack(name)

    def open_stack(self, name, stack=None):
        """
        Examples:
        stack.open_stack('data')
        stack.open_stack('data', ['2018-03-23'])
        stack.open_stack('data', ['2018-03-23', '2018-03-11'])
        stack.open_stack('phase15m')
        stack.open_stack('intf90m',[['2018-02-21','2018-03-11']])
        stack.open_stack('intf90m', stack.get_pairs([['2018-02-21','2018-03-11']]))
        """
        import xarray as xr
        import pandas as pd
        import numpy as np
        import glob
    
        if stack is None:
            # look for all stack files
            #filenames = self.get_filenames(['*'], name)[0]
            #filenames = self.get_filename(f'{name}_????????_????????')
            # like data_20180323.grd or intf60m_20230114_20230219.grd
            filenames = self._glob_re(name + '_[0-9]{8}(_[0-9]{8})*.grd')
        elif isinstance(stack, (list, tuple, np.ndarray)) and len(np.asarray(stack).shape) == 1:
            # dates
            filenames = self.get_filenames(np.asarray(stack), name)
        else:
            # pairs
            filenames = self.get_filenames(stack, name)
        #print ('filenames', filenames)

        data = xr.open_mfdataset(
            filenames,
            engine=self.netcdf_engine,
            parallel=True,
            concat_dim='stackvar',
            combine='nested'
        )
        
        if 'stack' in data.dims:
            if 'y' in data.coords and 'x' in data.coords:
                multi_index_names = ['y', 'x']
            elif 'lat' in data.coords and 'lon' in data.coords:
                multi_index_names = ['lat', 'lon']
            multi_index = pd.MultiIndex.from_arrays([data.y.values, data.x.values], names=multi_index_names)
            data = data.assign_coords(stack=multi_index).set_index({'stack': ['y', 'x']}).chunk({'stack': self.chunksize1d})
        else:
            dims = list(data.dims)
            data = data.chunk({dims[0]: 1, dims[1]: self.chunksize, dims[2]: self.chunksize})

        # revert dataarray converted to dataset
        data_vars = list(data.data_vars)
        if len(data_vars) == 1 and 'dataarray' in data.attrs:
            assert data.attrs['dataarray'] == data_vars[0]
            data = data[data_vars[0]]
    
        # attributes are empty when dataarray is prezented as dataset, convert it first
        # restore missed coordinates
        for dim in ['y', 'x', 'lat', 'lon']:
            if dim not in data.coords \
                and f'start_{dim}' in data.attrs \
                and f'step_{dim}' in data.attrs \
                and f'stop_{dim}' in data.attrs \
                and f'size_{dim}' in data.attrs:
                start = data.attrs[f'start_{dim}']
                step  = data.attrs[f'step_{dim}']
                stop  = data.attrs[f'stop_{dim}']
                size  = data.attrs[f'size_{dim}']
                coords = np.arange(start, stop+step/2, step)
                assert coords.size == size, 'Restored dimension has invalid size'
                #print (dim, start, step, stop, coords)
                data = data.assign_coords({dim: coords})
                # remove the system attributes
                del data.attrs[f'start_{dim}']
                del data.attrs[f'step_{dim}']
                del data.attrs[f'stop_{dim}']
                del data.attrs[f'size_{dim}']
    
        for dim in ['pair', 'date']:
            if dim in data.coords:
                if data[dim].shape == () or 'stack' in data.dims:
                    if data[dim].shape == ():
                        data = data.assign_coords(pair=('stackvar', [data[dim].values]))
                    data = data.rename({'stackvar': dim}).set_index({dim: dim})
                else:
                    data = data.swap_dims({'stackvar': dim})
    
        # convert string (or already timestamp) dates to dates
        for dim in ['date', 'ref', 'rep']:
            if dim in data.dims:
                if not data[dim].shape == ():
                    data[dim] = pd.to_datetime(data[dim])
                else:
                    data[dim].values = pd.to_datetime(data['date'].values)
    
        return data

#     # simple sequential realization is not suitable for a large stack
#     def save_stack(self, data, name, caption='Saving 2D grids stack'):
#         import xarray as xr
#         import dask
#         import os
#         import warnings
#         # suppress Dask warning "RuntimeWarning: invalid value encountered in divide"
#         warnings.filterwarnings('ignore')
#         warnings.filterwarnings('ignore', module='dask')
#         warnings.filterwarnings('ignore', module='dask.core')
# 
#         if isinstance(data, xr.Dataset):
#             stackvar = data[list(data.data_vars)[0]].dims[0]
#             is_dask = isinstance(data[list(data.data_vars)[0]].data, dask.array.Array)
#         elif isinstance(data, xr.DataArray):
#             stackvar = data.dims[0]
#             is_dask = isinstance(data.data, dask.array.Array)
#         else:
#             raise Exception('Argument grid is not xr.Dataset or xr.DataArray object')
#         #print ('is_dask', is_dask, 'stackvar', stackvar)
#         stacksize = data[stackvar].size
# 
#         for dim in ['y', 'x', 'lat', 'lon']:
#             if dim in data.dims:
#                 # use attributes to hold grid spacing to prevent xarray Dask saving issues
#                 data = data.drop(dim, dim=None).assign_attrs({
#                     f'start_{dim}': data[dim].values[0],
#                     f'step_{dim}':  data[dim].diff(dim).values[0],
#                     f'stop_{dim}':  data[dim].values[-1],
#                     f'size_{dim}':  data[dim].size
#                 })
# 
#         delayeds = []
#         digits = len(str(stacksize))
#         for ind in range(stacksize):
#             data_slice = data.isel({stackvar: ind})
#             if stackvar == 'date':
#                 stackval = str(data_slice[stackvar].dt.date.values)
#             else:
#                 stackval = data_slice[stackvar].item().split(' ')
#             #print ('stackval', stackval)
#             # save to NetCDF file
#             filename = self.get_filenames([stackval], name)[0]
#             #print ('filename', filename)
#             if os.path.exists(filename):
#                 os.remove(filename)
#             if isinstance(data, xr.Dataset):
#                 encoding = {varname: self._compression(data_slice[varname].shape) for varname in data.data_vars}
#             elif isinstance(data, xr.DataArray):
#                 encoding = {data.name: self._compression(data_slice.shape)}
#             else:
#                 raise Exception('Argument grid is not xr.Dataset or xr.DataArray object')
# 
#             delayed = data_slice.to_netcdf(filename,
#                                   encoding=encoding,
#                                   engine=self.netcdf_engine,
#                                   compute=not is_dask)
#             if is_dask:
#                 delayeds.append(delayed)
#                 del delayed
#             del data_slice
# 
#         if is_dask:
#             tqdm_dask(result := dask.persist(*delayeds), desc=caption)
#             # cleanup - sometimes writing NetCDF handlers are not closed immediately and block reading access
#             del delayeds, result
#             import gc; gc.collect()

    # use save_mfdataset
    def save_stack(self, data, name, caption='Saving 2D Stack', queue=None, timeout=None):
        import numpy as np
        import xarray as xr
        import pandas as pd
        import dask
        import os
        from dask.distributed import get_client
        import warnings
        # suppress Dask warning "RuntimeWarning: invalid value encountered in divide"
        warnings.filterwarnings('ignore')
        warnings.filterwarnings('ignore', module='dask')
        warnings.filterwarnings('ignore', module='dask.core')
        # Filter out Dask "Restarting worker" warnings
        warnings.filterwarnings("ignore", module="distributed.nanny")
        import logging
        # Suppress Dask "Restarting worker" warnings
        logging.getLogger('distributed.nanny').setLevel(logging.ERROR)
        # disable "distributed.utils_perf - WARNING - full garbage collections ..."
        try:
            from dask.distributed import utils_perf
            utils_perf.disable_gc_diagnosis()
        except ImportError:
            from distributed.gc import disable_gc_diagnosis
            disable_gc_diagnosis()
    
        # Dask cluster client
        client = get_client()
        
        if isinstance(data, xr.Dataset):
            stackvar = data[list(data.data_vars)[0]].dims[0]
            is_dask = isinstance(data[list(data.data_vars)[0]].data, dask.array.Array)
        elif isinstance(data, xr.DataArray):
            stackvar = data.dims[0]
            is_dask = isinstance(data.data, dask.array.Array)
        else:
            raise Exception('Argument grid is not xr.Dataset or xr.DataArray object')
        #print ('is_dask', is_dask, 'stackvar', stackvar)
        stacksize = data[stackvar].size
    
        if queue is None:
            queue = self.netcdf_queue
        if queue is None:
            # process all the stack items in a single operation
            queue = stacksize
    
        if 'stack' in data.dims and isinstance(data.coords['stack'].to_index(), pd.MultiIndex):
            # replace multiindex by sequential numbers 0,1,...
            data = data.reset_index('stack')
        
        for dim in ['y', 'x', 'lat', 'lon']:
            if dim in data.dims:
                # use attributes to hold grid spacing to prevent xarray Dask saving issues
                data = data.drop(dim, dim=None).assign_attrs({
                    f'start_{dim}': data[dim].values[0],
                    f'step_{dim}':  data[dim].diff(dim).values[0],
                    f'stop_{dim}':  data[dim].values[-1],
                    f'size_{dim}':  data[dim].size
                })
    
        if isinstance(data, xr.DataArray):
            data = data.to_dataset().assign_attrs({'dataarray': data.name})
        encoding = {varname: self._compression(data[varname].shape[1:]) for varname in data.data_vars}
        #print ('save_stack encoding', encoding)
    
        # Applying iterative processing to prevent Dask scheduler deadlocks.
        counter = 0
        digits = len(str(stacksize))
        # Splitting all the pairs into chunks, each containing approximately queue pairs.
        n_chunks = stacksize // queue if stacksize > queue else 1
        for chunk in np.array_split(range(stacksize), n_chunks):
            dss = [data.isel({stackvar: ind}) for ind in chunk]
            if stackvar == 'date':
                stackvals = [ds[stackvar].dt.date.values for ds in dss]
            else:
                stackvals = [ds[stackvar].item().split(' ') for ds in dss]
            # save to NetCDF file
            filenames = self.get_filenames(stackvals, name)
            #[os.remove(filename) for filename in filenames if os.path.exists(filename)]
            delayeds = xr.save_mfdataset(dss,
                                         filenames,
                                         encoding=encoding,
                                         engine=self.netcdf_engine,
                                         compute=not is_dask)
            # process lazy chunk
            if is_dask:
                if n_chunks > 1:
                    chunk_caption = f'{caption}: {(counter+1):0{digits}}...{(counter+len(chunk)):0{digits}} from {stacksize}'
                else:
                    chunk_caption = caption
                tqdm_dask(result := dask.persist(delayeds), desc=chunk_caption)
                del delayeds, result
                # cleanup - sometimes writing NetCDF handlers are not closed immediately and block reading access
                import gc; gc.collect()
                # cleanup - release all workers memory, call garbage collector before to prevent heartbeat errors
                if timeout is not None:
                    client.restart(timeout=timeout, wait_for_workers=True)
#                 # more granular control
#                 n_workers = len(client.nthreads())
#                 client.restart(wait_for_workers=False)
#                 client.wait_for_workers(n_workers, timeout=timeout)
            # update chunks counter
            counter += len(chunk)

#     # alternative realization
#     def save_stack(self, data, name, caption='Saving 2D Stack', queue=50):
#         import numpy as np
#         import xarray as xr
#         import dask
#         import os
#         from dask.distributed import get_client
#         import warnings
#         # suppress Dask warning "RuntimeWarning: invalid value encountered in divide"
#         warnings.filterwarnings('ignore')
#         warnings.filterwarnings('ignore', module='dask')
#         warnings.filterwarnings('ignore', module='dask.core')
#         # Filter out Dask "Restarting worker" warnings
#         warnings.filterwarnings("ignore", category=UserWarning, module="distributed.nanny")
#         import logging
#         # Suppress Dask "Restarting worker" warnings
#         logging.getLogger('distributed.nanny').setLevel(logging.ERROR)
#         # disable "distributed.utils_perf - WARNING - full garbage collections ..."
#         from dask.distributed import utils_perf
#         utils_perf.disable_gc_diagnosis()
# 
#         if isinstance(data, xr.Dataset):
#             stackvar = data[list(data.data_vars)[0]].dims[0]
#             is_dask = isinstance(data[list(data.data_vars)[0]].data, dask.array.Array)
#         elif isinstance(data, xr.DataArray):
#             stackvar = data.dims[0]
#             is_dask = isinstance(data.data, dask.array.Array)
#         else:
#             raise Exception('Argument grid is not xr.Dataset or xr.DataArray object')
#         #print ('is_dask', is_dask, 'stackvar', stackvar)
#         stacksize = data[stackvar].size
# 
#         if queue is None:
#             # process all the stack items in a single operation
#             queue = stacksize
# 
#         for dim in ['y', 'x', 'lat', 'lon']:
#             if dim in data.dims:
#                 # use attributes to hold grid spacing to prevent xarray Dask saving issues
#                 data = data.drop(dim, dim=None).assign_attrs({
#                     f'start_{dim}': data[dim].values[0],
#                     f'step_{dim}':  data[dim].diff(dim).values[0],
#                     f'stop_{dim}':  data[dim].values[-1],
#                     f'size_{dim}':  data[dim].size
#                 })
# 
#         if isinstance(data, xr.Dataset):
#             encoding = {varname: self._compression(data[varname].shape[1:]) for varname in data.data_vars}
#         elif isinstance(data, xr.DataArray):
#             encoding = {data.name: self._compression(data.shape[1:])}
#         else:
#             raise Exception('Argument data is not 3D xr.Dataset or xr.DataArray object')
#         #print ('encoding', encoding)
# 
#         # Applying iterative processing to prevent Dask scheduler deadlocks.
#         counter = 0
#         digits = len(str(stacksize))
#         # Splitting all the pairs into chunks, each containing approximately queue pairs.
#         n_chunks = stacksize // queue if stacksize >= queue else 1
#         for chunk in np.array_split(range(stacksize), n_chunks):
#             stack = [data.isel({stackvar: ind}) for ind in chunk]
#             assert len(stack) == len(chunk), 'ERROR: incorrect queue size'
#             if stackvar == 'date':
#                 stackvals = [ds[stackvar].dt.date.values for ds in stack]
#             else:
#                 stackvals = [ds[stackvar].item().split(' ') for ds in stack]
#             # NetCDF files
#             filenames = self.get_filenames(stackvals, name)
# 
#             delayeds = []
#             # prepare lazy chunk or process not lazy chunk
#             for data_slice, filename in zip(stack, filenames):
#                 #print ('filename', filename)
#                 if os.path.exists(filename):
#                     os.remove(filename)
#                 delayed = data_slice.to_netcdf(filename,
#                                       encoding=encoding,
#                                       engine=self.netcdf_engine,
#                                       compute=not is_dask)
#                 delayeds.append(delayed)
#                 del delayed, data_slice, filename
#             # process lazy chunk
#             if is_dask:
#                 chunk_caption = f'{caption}: {(counter+1):0{digits}}...{(counter+len(chunk)):0{digits}} from {stacksize}'
#                 tqdm_dask(dask.persist(delayeds), desc=chunk_caption)
#             # update chunks counter
#             counter += len(chunk)
#             del delayeds, stack
#             # cleanup - release all memory
#             get_client().restart()
#         # cleanup - sometimes writing NetCDF handlers are not closed immediately and block reading access
#         import gc; gc.collect()

    def delete_stack(self, name):
        import os

        filenames = self._glob_re(name + '_[0-9]{8}(_[0-9]{8})*.grd')
        #print ('filenames', filenames)
        for filename in filenames:
            if os.path.exists(filename):
                os.remove(filename)
