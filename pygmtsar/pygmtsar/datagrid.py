# ----------------------------------------------------------------------------
# PyGMTSAR
# 
# This file is part of the PyGMTSAR project: https://github.com/mobigroup/gmtsar
# 
# Copyright (c) 2022, Alexey Pechnikov
# 
# Licensed under the BSD 3-Clause License (see LICENSE for details)
# ----------------------------------------------------------------------------

class datagrid:
    """
    A class representing a data grid.

    Attributes
    ----------
    chunksize : int
        The chunk size for data compression. Default is 512.
    netcdf_engine : str
        The engine used for NetCDF file operations. Default is 'h5netcdf'.
    netcdf_complevel : int
        The compression level for data compression. Default is 3.
    noindex : np.uint32
        The NODATA index value for transform matrices.
    
    Notes
    ----------
    That's possible to define a special NetCDF backend for Docker environment or other cases:

    if os.path.exists('/.dockerenv') and not 'google.colab' in sys.modules:
        # use different NetCDF backend in Docker containers
        from pygmtsar import datagrid
        datagrid.netcdf_engine = 'netcdf4'
    
    """
    import numpy as np

    # Minimum valid Sentinel-1 radar amplitude from GMTSAR code
    #amplitude_threshold = 5.e-21
    # NetCDF options, see https://docs.xarray.dev/en/stable/user-guide/io.html#zarr-compressors-and-filters
    chunksize = 2048
    chunksize1d = 16384
    netcdf_engine = 'h5netcdf'
    #netcdf_engine = 'netcdf4'
    netcdf_chunksize = 512
    netcdf_chunksize1d = 65536
    netcdf_compression_algorithm = 'zlib'
    netcdf_complevel = -1
    netcdf_shuffle = True
    netcdf_queue = 16

    # define lost class variables due to joblib via arguments
    def _compression(self, shape=None, chunksize=None):
        """
        Return the compression options for a data grid.

        Parameters
        ----------
        shape : tuple, list, np.ndarray, optional
            The shape of the data grid. Required if chunksize is less than grid dimension sizes. Default is None.
        chunksize : int or tuple, optional
            The chunk size for data compression. If not specified, the class attribute chunksize is used.

        Returns
        -------
        dict
            A dictionary containing the compression options for the data grid.

        Examples
        --------
        Get the compression options for a data grid with shape (1000, 1000):

        >>> compression(shape=(1000, 1000))
        {'zlib': True, 'complevel': 3, 'chunksizes': (512, 512)}

        Get the compression options for a data grid with chunksize 256:

        >>> compression(chunksize=256)
        {'zlib': True, 'complevel': 3, 'chunksizes': (256, 256)}
        """
        import numpy as np

        if chunksize is None and len(shape) == 1:
            # (stacked) single-dimensional grid 
            chunksize = self.netcdf_chunksize1d
        elif chunksize is None:
            # common 2+D grid
            chunksize = self.netcdf_chunksize

        assert chunksize is not None, 'compression() chunksize is None'
        if isinstance(chunksize, (tuple, list, np.ndarray)):
            # use as is, it can be 2D or 3D grid (even 1D while it is not used for now)
            if shape is not None:
                assert len(shape) == len(chunksize), f'ERROR: defined shape and chunksize dimensions are not equal: {len(shape)} != {len(chunksize)}'
                chunksizes = tuple([chunksize[dim] if chunksize[dim]<shape[dim] else shape[dim] for dim in range(len(shape))])
            else:
                chunksizes = chunksize
        else:
            if shape is not None:
                # 2D or 3D grid
                chunksizes = []
                for idim in range(len(shape)):
                    chunksizes.append(chunksize if chunksize<shape[idim] else shape[idim])
                # set first dimension chunksize to 1 for 3D array
                if len(chunksizes) == 3:
                    chunksizes[0] = 1
                chunksizes = tuple(chunksizes)
            else:
                chunksizes=(chunksize, chunksize)
        opts = dict(chunksizes=chunksizes)
        if self.netcdf_compression_algorithm is not None and self.netcdf_complevel >= 0:
            opts[self.netcdf_compression_algorithm] = True
            opts['complevel'] = self.netcdf_complevel
            opts['shuffle'] = self.netcdf_shuffle
        return opts

    @staticmethod
    def is_ra(grid):
        """
        Checks if the given grid is in radar coordinates.

        Parameters
        ----------
        grid : xarray.DataArray
            The grid to check.

        Returns
        -------
        bool
            True if the grid is in radar coordinates, False otherwise.
        """
        dims = grid.dims
        coords = grid.coords
        if 'stack' in dims and 'y' in coords and 'x' in coords:
            return True
        if 'y' in dims and 'x' in dims:
            return True
        return False

    @staticmethod
    def is_geo(grid):
        """
        Checks if the given grid is in geographic coordinates.

        Parameters
        ----------
        grid : xarray.DataArray
            The grid to check.

        Returns
        -------
        bool
            True if the grid is in geographic coordinates, False otherwise.
        """
        dims = grid.dims
        coords = grid.coords
        if 'stack' in dims and 'lat' in coords and 'lon' in coords:
            return True
        if 'lat' in dims and 'lon' in dims:
            return True
        return False
 
    # da.dropna(dim=dim, how='all') is not fast at all
    @staticmethod
    def cropna(das, index=-1):
        """
        Crop the valid extent of a raster by removing rows and columns containing only NODATA values.

        Parameters
        ----------
        das : xarray.DataArray
            The input 2D or 3D grid to be cropped.

        Returns
        -------
        xarray.DataArray
            The cropped 2D or 3D grid.

        Examples
        --------
        Crop the valid extent of a raster:
        stack.cropna(grid)

        Notes
        -----
        This method crops the input grid by removing rows and columns that contain only NODATA values.
        It operates on 2D or 3D grids, where the NODATA values are represented as NaN values.
        The resulting grid has a reduced size, containing only the valid extent of the input grid.
        If the input grid is 3D, the cropping is performed along the dimensions other than 'pair' or 'date'.
        """
        # crop NaNs
        dims = [dim for dim in das.dims if dim != 'pair' and dim != 'date']
        dim0 = [dim for dim in das.dims if dim in ['pair', 'date']]
        #print ('dims', dims, 'dim0', dim0)
        assert len(dims) == 2, 'ERROR: the input should be 3D array with "pair" or "date" coordinate'
        # slow check using all the grids in the stack
        #da = das.min(dim0)
        # fast check using the only "index" grid in the stack
        da = das.isel({dim0[index]: index}) if dim0 != [] else das
        indexer = {}
        for dim in dims:
            da = da.dropna(dim=dim, how='all')
            dim_min, dim_max = da[dim].min().item(), da[dim].max().item()
            indexer[dim] = slice(dim_min, dim_max)
        #print ('indexer', indexer)
        return das.loc[indexer]
    
    # replacement for GMTSAR gaussians
    # gauss5x5 = np.genfromtxt('/usr/local/GMTSAR/share/gmtsar/filters/gauss5x5',skip_header=True)
    # gaussian_kernel(5,1) ~= gauss5x5
    @staticmethod
    def gaussian_kernel(size=(5,5), std=(1,1)):
        """
        Generate a 2D Gaussian kernel matrix.

        Parameters
        ----------
        size : tuple, optional
            The size of the kernel matrix in (rows, columns). Default is (5, 5).
        std : tuple, optional
            The standard deviation of the Gaussian distribution in (row_std, column_std). Default is (1, 1).

        Returns
        -------
        numpy.ndarray
            The 2D Gaussian kernel matrix.

        Examples
        --------
        Generate a 5x5 Gaussian kernel with standard deviation of 1 in both dimensions:
        gaussian_kernel(size=(5, 5), std=(1, 1))

        Generate a 3x3 Gaussian kernel with standard deviation of 0.5 in row dimension and 1 in column dimension:
        gaussian_kernel(size=(3, 3), std=(0.5, 1))
        """
        import numpy as np
        from scipy import signal
        matrix1 = signal.gaussian(size[0], std=std[0]).reshape(size[0], 1)
        matrix2 = signal.gaussian(size[1], std=std[1]).reshape(size[1], 1)
        matrix2d = np.outer(matrix1, matrix2)
        return matrix2d

    @staticmethod
    def get_bounds(geometry):
        import geopandas as gpd
        import xarray as xr
    
        if isinstance(geometry, (xr.DataArray, xr.Dataset)) and ('lat' in geometry.dims and 'lon' in geometry.dims):
            lon_start = geometry.lon.min().item()
            lat_start = geometry.lat.min().item()
            lon_end   = geometry.lon.max().item()
            lat_end   = geometry.lat.max().item()
            bounds = lon_start, lat_start, lon_end, lat_end
        elif isinstance(geometry, (xr.DataArray, xr.Dataset)):
            x_start = geometry.x.min().item()
            y_start = geometry.y.min().item()
            x_end   = geometry.x.max().item()
            y_end   = geometry.y.max().item()
            bounds = x_start, y_start, x_end, y_end
        elif isinstance(geometry, gpd.GeoDataFrame):
            bounds = geometry.dissolve().envelope.item().bounds
        elif isinstance(geometry, gpd.GeoSeries):
            bounds = geometry.union_all().envelope.bounds
        elif isinstance(geometry, tuple):
            # geometry is already bounds
            bounds = geometry
        else:
            bounds = geometry.bounds
        #print ('bounds', bounds)
        #lon_start, lat_start, lon_end, lat_end
        return bounds

#    @staticmethod
#    def nanconvolve2d(data, kernel, threshold=1/3.):
#        """
#        Convolution using generic kernel on a 2D array with NaNs
#        """
#        import numpy as np
#        import scipy.signal
#        # np.complex128 includes np.float64 real and imagine part
#        vals = data.astype(np.complex128)
#        #vals[np.isnan(data)] = 0
#        #vals[~np.isnan(data)] += 1j
#        nanmask = np.isnan(data)
#        vals[nanmask] = 0
#        vals[~nanmask] += 1j
#
#        conv = scipy.signal.convolve2d(vals, 
#                                      kernel.astype(np.complex128), 
#                                      mode='same', boundary='symm'
#                                     )
#        # suppress incorrect division warning
#        np.seterr(invalid='ignore')
#        return np.where(conv.imag >= threshold*np.sum(kernel), np.divide(conv.real, conv.imag), np.nan)

#     @staticmethod
#     def nanconvolve2d_gaussian(dataarray, sigmas, truncate):
#         """
#         Apply lazy convolution using Gaussian kernel on a 2D array with NaN values.
# 
#         Parameters
#         ----------
#         dataarray : xarray.DataArray
#             The input 2D array with NaN values.
#         sigmas : tuple
#             The standard deviations of the Gaussian kernel in (row_sigma, column_sigma).
#         truncate : float
#             The truncation factor for the Gaussian kernel.
# 
#         Returns
#         -------
#         xarray.DataArray
#             The convolved data array with NaN values.
# 
#         Examples
#         --------
#         Apply Gaussian convolution with sigmas (2, 2) and truncate factor 3 to a 2D data array:
#         nanconvolve2d_gaussian(dataarray, sigmas=(2, 2), truncate=3)
#         """
#         import xarray as xr
#         import dask
#         from dask_image.ndfilters import gaussian_filter as dask_gaussian_filter
# 
#         # this command works but it is slow
#         #da = dask.array.where(dask.array.isnan(dataarray), 0, 1j + dataarray)
#         # this command is fast and it replaces nan + 1j to to 0.+0.j
#         da = (dataarray + 1j).fillna(0).data
#         conv = dask_gaussian_filter(da, sigmas, mode='reflect', truncate=truncate)
#         da_conv = xr.DataArray(conv.real/conv.imag, coords=dataarray.coords, name=dataarray.name)
#         return da_conv

    def nearest_grid(self, in_grid, search_radius_pixels=None):
        """
        Perform nearest neighbor interpolation on a 2D grid.

        Parameters
        ----------
        in_grid : xarray.DataArray
            The input 2D grid to be interpolated.
        search_radius_pixels : int, optional
            The interpolation distance in pixels. If not provided, the default is set to the chunksize of the Stack object.

        Returns
        -------
        xarray.DataArray
            The interpolated 2D grid.

        Examples
        --------
        Fill gaps in the specified grid using nearest neighbor interpolation:
        stack.nearest_grid(grid)

        Notes
        -----
        This method performs nearest neighbor interpolation on a 2D grid. It replaces the NaN values in the input grid with
        the nearest non-NaN values. The interpolation is performed within a specified search radius in pixels.
        If a search radius is not provided, the default search radius is set to the chunksize of the Stack object.
        """
        from scipy.spatial import cKDTree
        import xarray as xr
        import numpy as np

        assert in_grid.chunks is not None, 'nearest_grid() input grid chunks are not defined'

        if search_radius_pixels is None:
            search_radius_pixels = self.chunksize
        elif search_radius_pixels <= 0:
            print (f'NOTE: interpolation ignored for search_radius_pixels={search_radius_pixels}')
            return in_grid
        else:
            assert search_radius_pixels <= self.chunksize, \
                f'ERROR: apply nearest_grid_pixels() multiple times to fill gaps more than {self.chunksize} pixels chunk size'

        def func(grid, y, x, distance, scaley, scalex):

            grid1d = grid.reshape(-1).copy()
            nanmask0 = np.isnan(grid1d)
            # all the pixels already defined
            if np.all(~nanmask0):
                return grid

            # crop full grid subset to search for missed values neighbors
            ymin = y.min()-scaley*distance-1
            ymax = y.max()+scaley*distance+1
            xmin = x.min()-scalex*distance-1
            xmax = x.max()+scalex*distance+1
            if self.is_ra(in_grid):
                data = in_grid.sel(y=slice(ymin, ymax), x=slice(xmin, xmax))
                ys, xs = data.y, data.x
            else:
                data = in_grid.sel(lat=slice(ymin, ymax), lon=slice(xmin, xmax))
                ys, xs = data.lat, data.lon
            # compute dask arrays to prevent ineffective index lookup
            ys, xs = [vals.values.reshape(-1) for vals in xr.broadcast(ys, xs)]
            data1d = data.values.reshape(-1)
            nanmask = np.isnan(data1d)
            # all the subset pixels are empty, the search is useless
            if np.all(nanmask):
                return grid

            # build index tree for all the valid subset values
            source_yxs = np.stack([ys[~nanmask]/scaley, xs[~nanmask]/scalex], axis=1)
            tree = cKDTree(source_yxs, compact_nodes=False, balanced_tree=False)

            # query the index tree for all missed values neighbors
            target_yxs = np.stack([(y/scaley).reshape(-1)[nanmask0], (x/scalex).reshape(-1)[nanmask0]], axis=1)
            #assert 0, target_yxs
            d, inds = tree.query(target_yxs, k = 1, distance_upper_bound=distance, workers=1)
            # fill missed values using neighbors when these ones are found
            inds = np.where(np.isinf(d), 0, inds)
            grid1d[nanmask0] = np.where(np.isinf(d), np.nan, data1d[~nanmask][inds])
            return grid1d.reshape(grid.shape)

        coords = ['y', 'x'] if self.is_ra(in_grid) else ['lat', 'lon']
        scale = [in_grid[coord].diff(coord).item(0) for coord in coords]
        yy = xr.DataArray(in_grid[coords[0]]).chunk(-1)
        xx = xr.DataArray(in_grid[coords[1]]).chunk(-1)
        ys, xs = xr.broadcast(yy,xx)

        # xarray wrapper
        grid = xr.apply_ufunc(
            func,
            in_grid,
            ys.chunk(in_grid.chunks),
            xs.chunk(in_grid.chunks),
            dask='parallelized',
            vectorize=False,
            output_dtypes=[np.float32],
            dask_gufunc_kwargs={'distance': search_radius_pixels, 'scaley': scale[0], 'scalex': scale[1]},
        )
        assert grid.chunks is not None, 'nearest_grid() output grid chunks are not defined'
        return grid

    def get_spacing(self, grid=1):
        """
        Compute the ground pixel size in meters for the default processing grid or the defined one.

        Parameters
        ----------
        grid : tuple or xarray.DataArray, optional
            A pair of x, y grid decimation coefficients or a 2D or 3D Xarray DataArray representing the decimation grid.
            The default is (1, 4) for the default processing grid.

        Returns
        -------
        tuple
            The ground pixel size(s) in meters.

        Examples
        --------
        Get the default ground pixel size:
        stack.get_spacing()
        >>> (14.0, 15.7)

        Get the ground pixel size for an unwrapped phase grid with a decimation of {'y': 2, 'x': 2}:
        stack.get_spacing(unwrap)
        >>> (27.9, 29.5)

        Notes
        -----
        This method computes the ground pixel size in meters for the default processing grid or a user-defined grid.
        The pixel size is calculated based on the azimuth and range pixel sizes obtained from the processing parameters.
        If a grid is provided, the pixel sizes are adjusted according to the grid decimation coefficients.
        The pixel sizes are rounded to one decimal place.
        """
        # pixel size in meters
        return self.PRM().get_spacing(grid)

    def get_coarsen(self, factor):
        import numpy as np

        # expand simplified definition
        if not isinstance(factor, (list,tuple, np.ndarray)):
            coarsens = (factor, factor)
        else:
            coarsens = factor

        types = [type(coarsen) for coarsen in coarsens]
        assert types[0] == types[1], f'Mixed coarsen datatypes are not allowed: {types}'
        if types[0] == int:
            # defined in pixels, as required
            return coarsens

        # float coarsen should be defined in meters, convert to pixels
        #print ('coarsens', coarsens)
        psizes = self.get_spacing()
        #print ('psizes', psizes)
        # follow same agreement as Stack.decimator() function for rounding
        if coarsens[1] > 4*psizes[1]:
            coarsens = np.round([coarsens[0]/psizes[0], coarsens[1]/psizes[1]/4]).astype(int)
            coarsens[1] = 4 * coarsens[1]
        else:
            coarsens = np.round([coarsens[0]/psizes[0], coarsens[1]/psizes[1]]).astype(int)

        return coarsens

    @staticmethod
    def calculate_coarsen_start(da, name, spacing, grid_factor=1):
        """
        Calculate start coordinate to align coarsened grids.
        """
        import numpy as np
        for i in range(spacing):
            values = da[name].isel({name: slice(i, None)}).coarsen({name: spacing}, boundary='trim').mean().values
            delta = np.floor(values[0] % (spacing*grid_factor))
            #print ('i', i, 'delta', delta, 'values', values[:5])
            if delta == 0:
                #print ('calculate_start', name, i)
                return i
        return None

#     #decimator = lambda da: da.coarsen({'y': 2, 'x': 2}, boundary='trim').mean()
#     def decimator(self, resolution=60, grid=(1, 4), func='mean', debug=False):
#         """
#         Return function for pixel decimation to the specified output resolution.
# 
#         Parameters
#         ----------
#         resolution : int, optional
#             DEM grid resolution in meters. The same grid is used for geocoded results output.
#         grid : tuple, optional
#             Grid size for pixel decimation in the format (vertical, horizontal).
#         debug : bool, optional
#             Boolean flag to print debug information.
# 
#         Returns
#         -------
#         callable
#             Post-processing lambda function.
# 
#         Examples
#         --------
#         Decimate computed interferograms to default DEM resolution 60 meters:
#         decimator = stack.decimator()
#         stack.intf(pairs, func=decimator)
#         """
#         import numpy as np
#         import dask
# 
#         # special cases: scale factor should be 4*N or 2*N to prevent rounding issues
#         # grid can be defined as [] or () or xarray dataarray
#         grid_as_coeffs = isinstance(grid,(list, tuple))
#         if   (grid_as_coeffs and grid==(1, 1)) or (not grid_as_coeffs and grid.x.diff('x')[0].item()) == 1:
#             xscale0 = 4
#         elif (grid_as_coeffs and grid==(1, 2)) or (not grid_as_coeffs and grid.x.diff('x')[0].item()) == 2:
#             xscale0 = 2
#         else:
#             xscale0 = 1
#         if debug:
#             print (f'DEBUG: scale to square grid: xscale0={xscale0}')
# 
#         dy, dx = self.get_spacing(grid)
#         yscale, xscale = int(np.round(resolution/dy)), int(np.round(resolution/dx/xscale0))
#         if debug:
#             print (f'DEBUG: ground pixel size in meters: y={dy}, x={dx}')
#         if yscale <= 1 and xscale <= 1 and xscale0==1:
#             # decimation impossible
#             if debug:
#                 print (f'DEBUG: decimator = lambda da: da')
#             return lambda da: da
#         if debug:
#             print (f"DEBUG: decimator = lambda da: da.coarsen({{'y': {yscale}, 'x': {xscale0*xscale}}}, boundary='trim').{func}()")
# 
#         # decimate function
#         def decimator(da):
#             # workaround for Google Colab when we cannot save grids with x,y coordinate names
#             # also supports geographic coordinates
#             yname = [varname for varname in ['y', 'lat', 'a'] if varname in da.dims][0]
#             xname = [varname for varname in ['x', 'lon', 'r'] if varname in da.dims][0]
#             coarsen_args = {yname: yscale, xname: xscale0*xscale}
#             #if debug:
#             #    print (f"Decimate y variable '{yname}' for scale 1/{yscale} and x variable '{xname}' for scale 1/{xscale}")
#             # avoid creating the large chunks
#             with dask.config.set(**{'array.slicing.split_large_chunks': True}):
#                 if func == 'mean':
#                     return da.coarsen(coarsen_args, boundary='trim').mean()
#                 elif func == 'min':
#                     return da.coarsen(coarsen_args, boundary='trim').min()
#                 elif func == 'max':
#                     return da.coarsen(coarsen_args, boundary='trim').max()
#                 elif func == 'count':
#                     return da.coarsen(coarsen_args, boundary='trim').count()
#                 elif func == 'sum':
#                     return da.coarsen(coarsen_args, boundary='trim').sum()
#                 else:
#                     raise ValueError(f"Unsupported function {func}. Should be 'mean','min','max','count', or 'sum'")
# 
#         # return callback function
#         return lambda da: decimator(da)

#     # anti-aliasing filter and downscaling, double filter (potentially faster)
#     def antialiasing_downscale(self, da, wavelength, truncate=3, coarsen=(1,4)):
#         import xarray as xr
#         import numpy as np
#         import dask
#         from dask_image.ndfilters import gaussian_filter as dask_gaussian_filter
#         # coarse grid to square cells
#         if coarsen is not None:
#             conv = dask_gaussian_filter(da.data, coarsen, mode='reflect', truncate=2)
#             da_square = xr.DataArray(conv, coords=da.coords, name=da.name).coarsen({'y': coarsen[0], 'x': coarsen[1]}, boundary='trim').mean()
#         # antialiasing (multi-looking) filter
#         if wavelength is None:
#             return da_square
#         dy, dx = self.get_spacing()
#         print ('DEBUG dy, dx', dy, dx)
#         sigmas = int(np.round(wavelength/dy/coarsen[0])), int(np.round(wavelength/dx/coarsen[1]))
#         print ('DEBUG sigmas', sigmas)
#         conv = dask_gaussian_filter(da_square.data, sigmas, mode='reflect', truncate=2)
#         return xr.DataArray(conv, coords=da_square.coords, name=da.name)
    # anti-aliasing filter and downscaling, single filter (potentially more accurate)
#     # coarsen = None disables downscaling and uses wavelength to filter
#     # coarsen=1 disables downscaling and use coarsen/cutoff filter
#     def antialiasing_downscale(self, da, weight=None, wavelength=None, coarsen=(1,4), debug=False):
#         import xarray as xr
#         import numpy as np
#         import dask
#         from dask_image.ndfilters import gaussian_filter as dask_gaussian_filter
#         # GMTSAR constant 5.3 defines half-gain at filter_wavelength
#         # https://github.com/gmtsar/gmtsar/issues/411
#         cutoff = 5.3
# 
#         # expand simplified definition
#         if coarsen is not None and not isinstance(coarsen, (list,tuple, np.ndarray)):
#             coarsen = (coarsen, coarsen)
# 
#         # allow this case to save the original grid resolution
#         if wavelength is None and coarsen is None:
#             return da
# 
#         # antialiasing (multi-looking) filter
#         if wavelength is None:
#             sigmas = np.round([coarsen[0]/cutoff, coarsen[1]/cutoff], 2)
#         else:
#             dy, dx = self.get_spacing(da)
#             #print ('DEBUG dy, dx', dy, dx)
#             #sigmas = int(np.round(wavelength/dy/coarsen[0])), int(np.round(wavelength/dx))
#             sigmas = np.round([wavelength/cutoff/dy, wavelength/cutoff/dx], 2)
#         if debug:
#             print ('DEBUG: antialiasing_downscale sigmas', sigmas, 'for specified wavelength', wavelength)
# 
#         # weighted and not weighted convolution
#         if weight is None:
#             if debug:
#                 print ('DEBUG: antialiasing_downscale not weighted filtering')
#             conv = dask_gaussian_filter(da.data, sigmas, mode='reflect', truncate=2)
#         else:
#             assert da.shape == weight.shape, f'Different shapes for raster {da.shape} and weight {weight.shape}'
#             assert da.dims == weight.dims, f'Different dimension names for raster {da.dims} and weight {weight.dims}'
#             if debug:
#                 print ('DEBUG: antialiasing_downscale weighted filtering')
#             #conv = dask_gaussian_filter(((1j + da)*weight).data, sigmas, mode='reflect', truncate=2)
#             # replace nan + 1j to to 0.+0.j
#             da  = ((1j + da) * weight).fillna(0)
#             conv = dask_gaussian_filter(da.data, sigmas, mode='reflect', truncate=2)
#             conv = conv.real/conv.imag
# 
#         da_conv = xr.DataArray(conv, coords=da.coords, name=da.name)
#         # calculate the initial dataarray chunk sizes per dimensions to restore them
#         # it works faster when we prevent small chunks usage
#         chunksizes = (np.max(da.chunksizes['y']), np.max(da.chunksizes['x']))
#         if coarsen is not None:
#             # coarse grid to square cells
#             return da_conv.coarsen({'y': coarsen[0], 'x': coarsen[1]}, boundary='trim').mean().chunk(chunksizes)
#         return da_conv.chunk(chunksizes)
