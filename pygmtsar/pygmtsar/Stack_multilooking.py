# ----------------------------------------------------------------------------
# PyGMTSAR
# 
# This file is part of the PyGMTSAR project: https://github.com/mobigroup/gmtsar
# 
# Copyright (c) 2023, Alexey Pechnikov
# 
# Licensed under the BSD 3-Clause License (see LICENSE for details)
# ----------------------------------------------------------------------------
from .Stack_phasediff import Stack_phasediff
from .utils import utils

class Stack_multilooking(Stack_phasediff):

    #decimator = lambda da: da.coarsen({'y': 2, 'x': 2}, boundary='trim').mean()
    def decimator(self, resolution=60, grid=(1, 4), func='mean', debug=False):
        """
        Return function for pixel decimation to the specified output resolution.

        Parameters
        ----------
        resolution : int, optional
            DEM grid resolution in meters. The same grid is used for geocoded results output.
        grid : tuple, optional
            Grid size for pixel decimation in the format (vertical, horizontal).
        debug : bool, optional
            Boolean flag to print debug information.

        Returns
        -------
        callable
            Post-processing lambda function.

        Examples
        --------
        Decimate computed interferograms to default DEM resolution 60 meters:
        decimator = stack.decimator()
        stack.intf(pairs, func=decimator)
        """
        import numpy as np
        import dask
        import warnings
        # suppress Dask warning "RuntimeWarning: invalid value encountered in divide"
        warnings.filterwarnings('ignore')
        warnings.filterwarnings('ignore', module='dask')
        warnings.filterwarnings('ignore', module='dask.core')

        # special cases: scale factor should be 4*N or 2*N to prevent rounding issues
        # grid can be defined as [] or () or xarray dataarray
        grid_as_coeffs = isinstance(grid,(list, tuple))
        if   (grid_as_coeffs and grid==(1, 1)) or (not grid_as_coeffs and grid.x.diff('x')[0].item()) == 1:
            xscale0 = 4
        elif (grid_as_coeffs and grid==(1, 2)) or (not grid_as_coeffs and grid.x.diff('x')[0].item()) == 2:
            xscale0 = 2
        else:
            xscale0 = 1
        if debug:
            print (f'DEBUG: scale to square grid: xscale0={xscale0}')

        dy, dx = self.get_spacing(grid)
        yscale, xscale = int(np.round(resolution/dy)), int(np.round(resolution/dx/xscale0))
        if debug:
            print (f'DEBUG: ground pixel size in meters: y={dy:.1f}, x={dx:.1f}')
        if yscale <= 1 and xscale <= 1 and xscale0==1:
            # decimation impossible
            if debug:
                print (f'DEBUG: decimator = lambda da: da')
            return lambda da: da
        if debug:
            print (f"DEBUG: decimator = lambda da: da.coarsen({{'y': {yscale}, 'x': {xscale0*xscale}}}, boundary='trim').{func}()")

        # decimate function
        def decimator(da):
            import warnings
            # suppress Dask warning "RuntimeWarning: invalid value encountered in divide"
            warnings.filterwarnings('ignore')
            warnings.filterwarnings('ignore', module='dask')
            warnings.filterwarnings('ignore', module='dask.core')
            # unstack data if needed
            if 'stack' in da.dims:
                # .unstack() is too slow on lazy grids in some of Xarray/Dask versions
                da = da.compute().unstack('stack')
            # workaround for Google Colab when we cannot save grids with x,y coordinate names
            # also supports geographic coordinates
            yname = [varname for varname in ['y', 'lat', 'a'] if varname in da.dims][0]
            xname = [varname for varname in ['x', 'lon', 'r'] if varname in da.dims][0]
            coarsen_args = {yname: yscale, xname: xscale0*xscale}
            # calculate coordinate offsets to align coarsened grids
            y0 = self.calculate_coarsen_start(da, yname, yscale,         grid[0])
            x0 = self.calculate_coarsen_start(da, xname, xscale0*xscale, grid[1])
            # avoid creating the large chunks
            with dask.config.set(**{'array.slicing.split_large_chunks': True}):
                #if func not in ['mean', 'min', 'max', 'count', 'sum']:
                #    raise ValueError(f"Unsupported function {func}. Should be 'mean','min','max','count', or 'sum'")
                # return getattr(da.coarsen(coarsen_args, boundary='trim'), func)()\
                #        .chunk({yname: self.chunksize, xname: self.chunksize})
                return getattr(da.isel({yname: slice(y0, None), xname: slice(x0, None)})\
                       .coarsen(coarsen_args, boundary='trim'), func)()\
                       .chunk({yname: self.chunksize, xname: self.chunksize})

        # return callback function and set common chunk size
        return lambda da: decimator(da)
    
#     # coarsen = None disables downscaling and uses wavelength to filter
#     # coarsen=1 disables downscaling and use coarsen/cutoff filter
#     def multilooking(self, data, weight=None, wavelength=None, coarsen=None, debug=False):
#         import xarray as xr
#         import numpy as np
#         import dask
#         #from dask_image.ndfilters import gaussian_filter as dask_gaussian_filter
#         
#         # GMTSAR constant 5.3 defines half-gain at filter_wavelength
#         # https://github.com/gmtsar/gmtsar/issues/411
#         cutoff = 5.3
# 
#         # expand simplified definition
#         if coarsen is not None and not isinstance(coarsen, (list, tuple, np.ndarray)):
#             coarsen = (coarsen, coarsen)
# 
#         # allow this case to save the original grid resolution
#         if wavelength is None and coarsen is None:
#             return data
# 
#         # antialiasing (multi-looking) filter
#         if wavelength is None:
#             sigmas = [coarsen[0]/cutoff, coarsen[1]/cutoff]
#             if debug:
#                 print (f'DEBUG: multilooking sigmas ({sigmas[0]:.2f}, {sigmas[1]:.2f}), for specified coarsen {coarsen}')
#         else:
#             dy, dx = self.get_spacing(data)
#             #print ('DEBUG dy, dx', dy, dx)
#             #sigmas = int(np.round(wavelength/dy/coarsen[0])), int(np.round(wavelength/dx))
#             sigmas = [wavelength/cutoff/dy, wavelength/cutoff/dx]
#             if debug:
#                 print (f'DEBUG: multilooking sigmas ({sigmas[0]:.2f}, {sigmas[1]:.2f}), for specified wavelength {wavelength:.1f}')
# 
#         # weighted and not weighted convolution on float and complex float data
#         def apply_filter(data, weight, sigmas, truncate=2):
#             if np.issubdtype(data.dtype, np.complexfloating):
#                 #print ('complexfloating')
#                 parts = []
#                 for part in [data.real, data.imag]:
#                     data_complex  = ((1j + part) * (weight if weight is not None else 1)).fillna(0)
#                     conv_complex = dask_gaussian_filter(data_complex.data, sigmas, mode='reflect', truncate=truncate)
#                     #conv = conv_complex.real/conv_complex.imag
#                     # to prevent "RuntimeWarning: invalid value encountered in divide" even when warning filter is defined
#                     conv = dask.array.where(conv_complex.imag == 0, np.nan, conv_complex.real/(conv_complex.imag + 1e-17))
#                     del data_complex, conv_complex
#                     parts.append(conv)
#                     del conv
#                 conv = parts[0] + 1j*parts[1]
#                 del parts
#             else:
#                 #print ('floating')
#                 # replace nan + 1j to to 0.+0.j
#                 data_complex  = ((1j + data) * (weight if weight is not None else 1)).fillna(0)
#                 conv_complex = dask_gaussian_filter(data_complex.data, sigmas, mode='reflect', truncate=truncate)
#                 #conv = conv_complex.real/conv_complex.imag
#                 # to prevent "RuntimeWarning: invalid value encountered in divide" even when warning filter is defined
#                 conv = dask.array.where(conv_complex.imag == 0, np.nan, conv_complex.real/(conv_complex.imag + 1e-17))
#                 del data_complex, conv_complex
#             return conv
# 
#         if isinstance(data, xr.Dataset):
#             dims = data[list(data.data_vars)[0]].dims
#         else:
#             dims = data.dims
# 
#         if len(dims) == 2:
#             stackvar = None
#         else:
#             stackvar = dims[0]
#         #print ('stackvar', stackvar)
# 
#         if weight is not None:
#             # for InSAR processing expect 2D weights
#             assert isinstance(weight, xr.DataArray) and len(weight.dims)==2, \
#                 'ERROR: multilooking weight should be 2D DataArray'
#         
#         if weight is not None and len(data.dims) == len(weight.dims):
#             #print ('2D check shape weighted')
#             # single 2D grid processing
#             if isinstance(data, xr.Dataset):
#                 for varname in data.data_vars:
#                     assert data[varname].shape == weight.shape, \
#                         f'ERROR: multilooking data[{varname}] and weight variables have different shape'
#             else:
#                 assert data.shape == weight.shape, 'ERROR: multilooking data and weight variables have different shape'
#         elif weight is not None and len(data.dims) == len(weight.dims) + 1:
#             #print ('3D check shape weighted')
#             # stack of 2D grids processing
#             if isinstance(data, xr.Dataset):
#                 for varname in data.data_vars:
#                     assert data[varname].shape[1:] == weight.shape, \
#                         f'ERROR: multilooking data[{varname}] slice and weight variables have different shape'
#             else:
#                 assert data.shape[1:] == weight.shape, 'ERROR: multilooking data slice and weight variables have different shape'
# 
#         stack =[]
#         for ind in range(len(data[stackvar]) if stackvar is not None else 1):
#             if isinstance(data, xr.Dataset):
#                 #print (f'Dataset ind:{ind}')
#                 data_convs = []
#                 for key in data.data_vars:
#                     conv = utils.nanconvolve2d_gaussian(data[key][ind] if stackvar is not None else data[key],
#                                         weight,
#                                         sigmas)
#                     data_conv = xr.DataArray(conv, dims=data[key].dims[1:] if stackvar is not None else data[key].dims, name=data[key].name)
#                     del conv
#                     data_convs.append(data_conv)
#                     del data_conv
#                 stack.append(xr.merge(data_convs))
#                 del data_convs
#             else:
#                 #print (f'DataArray ind:{ind}')
#                 conv = utils.nanconvolve2d_gaussian(data[ind]   if stackvar is not None else data,
#                                     weight,
#                                     sigmas)
#                 data_conv = xr.DataArray(conv, dims=data.dims[1:] if stackvar is not None else data.dims, name=data.name)
#                 del conv
#                 stack.append(data_conv)
#                 del data_conv
# 
#         if stackvar is not None:
#             #print ('3D')
#             ds = xr.concat(stack, dim=stackvar).assign_coords(data.coords)
#         else:
#             #print ('2D')
#             ds = stack[0].assign_coords(data.coords)
#         del stack
# 
#         # it works faster when we prevent small output chunks
#         chunksizes = {'y': self.chunksize, 'x': self.chunksize}
#         if coarsen is not None:
#             # coarse grid typically to square cells
#             return ds.coarsen({'y': coarsen[0], 'x': coarsen[1]}, boundary='trim').mean().chunk(chunksizes)
#         return ds.chunk(chunksizes)

    def multilooking(self, data, weight=None, wavelength=None, coarsen=None, debug=False):
        import xarray as xr
        import numpy as np
        import dask
    
        # GMTSAR constant 5.3 defines half-gain at filter_wavelength
        cutoff = 5.3
    
        # Expand simplified definition of coarsen
        coarsen = (coarsen, coarsen) if coarsen is not None and not isinstance(coarsen, (list, tuple, np.ndarray)) else coarsen
    
        # no-op, processing is needed
        if wavelength is None and coarsen is None:
            return data
    
        # calculate sigmas based on wavelength or coarsen
        if wavelength is not None:
            dy, dx = self.get_spacing(data)
            sigmas = [wavelength / cutoff / dy, wavelength / cutoff / dx]
            if debug:
                print(f'DEBUG: multilooking sigmas ({sigmas[0]:.2f}, {sigmas[1]:.2f}), wavelength {wavelength:.1f}')
        else:
            sigmas = [coarsen[0] / cutoff, coarsen[1] / cutoff]
            if debug:
                print(f'DEBUG: multilooking sigmas ({sigmas[0]:.2f}, {sigmas[1]:.2f}), coarsen {coarsen}')

        if isinstance(data, xr.Dataset):
            dims = data[list(data.data_vars)[0]].dims
        else:
            dims = data.dims

        if len(dims) == 2:
            stackvar = None
        else:
            stackvar = dims[0]
        #print ('stackvar', stackvar)

        if weight is not None:
            # for InSAR processing expect 2D weights
            assert isinstance(weight, xr.DataArray) and len(weight.dims)==2, \
                'ERROR: multilooking weight should be 2D DataArray'
        
        if weight is not None and len(data.dims) == len(weight.dims):
            #print ('2D check shape weighted')
            # single 2D grid processing
            if isinstance(data, xr.Dataset):
                for varname in data.data_vars:
                    assert data[varname].shape == weight.shape, \
                        f'ERROR: multilooking data[{varname}] and weight variables have different shape'
            else:
                assert data.shape == weight.shape, 'ERROR: multilooking data and weight variables have different shape'
        elif weight is not None and len(data.dims) == len(weight.dims) + 1:
            #print ('3D check shape weighted')
            # stack of 2D grids processing
            if isinstance(data, xr.Dataset):
                for varname in data.data_vars:
                    assert data[varname].shape[1:] == weight.shape, \
                        f'ERROR: multilooking data[{varname}] slice and weight variables have different shape \
                        ({data[varname].shape[1:]} vs {weight.shape})'
            else:
                assert data.shape[1:] == weight.shape, f'ERROR: multilooking data slice and weight variables have different shape \
                ({data.shape[1:]} vs {weight.shape})'

        # process a slice of dataarray
        def process_slice(slice_data):
            conv = utils.nanconvolve2d_gaussian(slice_data, weight, sigmas)
            return xr.DataArray(conv, dims=slice_data.dims, name=slice_data.name)

        # process stack of dataarray slices
        def process_slice_var(dataarray):    
            if stackvar:
                stack = [process_slice(dataarray[ind]) for ind in range(len(dataarray[stackvar]))]
                return xr.concat(stack, dim=stackvar).assign_coords(dataarray.coords)
            else:
                return process_slice(dataarray).assign_coords(dataarray.coords)

        if isinstance(data, xr.Dataset):
            ds = xr.Dataset({varname: process_slice_var(data[varname]) for varname in data.data_vars})
        else:
            ds = process_slice_var(data)
    
        # Set chunk size
        chunksizes = {'y': self.chunksize, 'x': self.chunksize}

        if coarsen:
            # calculate coordinate offsets to align coarsened grids
            y0 = self.calculate_coarsen_start(ds, 'y', coarsen[0])
            x0 = self.calculate_coarsen_start(ds, 'x', coarsen[1])
            return ds.isel({'y': slice(y0, None), 'x': slice(x0, None)})\
                     .coarsen({'y': coarsen[0], 'x': coarsen[1]}, boundary='trim')\
                     .mean()\
                     .chunk(chunksizes)

        return ds.chunk(chunksizes)
