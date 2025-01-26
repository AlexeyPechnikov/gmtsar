# ----------------------------------------------------------------------------
# PyGMTSAR
# 
# This file is part of the PyGMTSAR project: https://github.com/mobigroup/gmtsar
# 
# Copyright (c) 2023, Alexey Pechnikov
# 
# Licensed under the BSD 3-Clause License (see LICENSE for details)
# ----------------------------------------------------------------------------
from .Stack_stl import Stack_stl
from .tqdm_dask import tqdm_dask

class Stack_ps(Stack_stl):

    def get_ps(self, name='ps'):
        return self.open_cube(name)

    #from pygmtsar import tqdm_dask
    #Stack.ps = ps    
    #stack.ps(interactive=True)
    #stack.ps()
    #adi = stack.open_grids(None, 'ps')
    #adi
    #ps_decimator = stack.pixel_decimator(resolution=60, grid=adi, debug=True)
    #adi_dec = adi.coarsen({'y': 4, 'x': 16}, boundary='trim').min()
    #adi_dec
    # define PS candidates using Amplitude Dispersion Index (ADI)
    def compute_ps(self, geometry=None, dates=None, data='auto', name='ps', interactive=False):
        import xarray as xr
        import numpy as np
        import dask
        import os
        import warnings
        # suppress Dask warning "RuntimeWarning: invalid value encountered in divide"
        warnings.filterwarnings('ignore')
        warnings.filterwarnings('ignore', module='dask')
        warnings.filterwarnings('ignore', module='dask.core')

        if isinstance(data, str) and data == 'auto':
            # open SLC data as real intensities
            data = np.square(np.abs(self.open_data(dates=dates)))

        if geometry is not None:
            bounds = self.get_bounds(geometry)
            data = data.sel(y=slice(bounds[1], bounds[3]), x=slice(bounds[0], bounds[2]))
            if isinstance(geometry, xr.DataArray):
                data = data.where(geometry).where(np.isfinite(geometry))

        # normalize image amplitudes (intensities)
        # dask.persist returns tuple
        tqdm_dask(mean := dask.persist(data.mean(dim=['y','x']))[0], desc='Intensity Normalization')
        # workaround: apply compute() to calculated mean to prevent weird dask 2025.1.0 error:
        # Exception: 'AttributeError("\'tuple\' object has no attribute \'size\'")'
        mean = mean.compute()
        data_norm = data * (mean.mean(dim='date') / mean)
        del data
        # compute average and std.dev.
        ds = xr.merge([
            data_norm.mean(dim='date').rename('average'),
            data_norm.std(dim='date').rename('deviation'),
            mean.rename('stack_average')
        ])
        del mean, data_norm
        if interactive:
            return ds
        self.save_cube(ds, name, 'Compute Stability Measures')
        del ds

    def psfunction(self, ps='auto', name='ps'):
        import numpy as np
        if isinstance(ps, str) and ps == 'auto':
            ps = self.get_ps(name)
        psfunction = (ps.average/(2*ps.deviation))
        return psfunction.where(np.isfinite(psfunction)).rename('psf')

    def plot_psfunction(self, data='auto', caption='PS Function', cmap='gray', quantile=None, vmin=None, vmax=None, **kwargs):
        import numpy as np
        import pandas as pd
        import matplotlib.pyplot as plt

        if isinstance(data, str) and data == 'auto':
            data = self.psfunction()
        elif 'stack' in data.dims and isinstance(data.coords['stack'].to_index(), pd.MultiIndex):
            data = data.unstack('stack')

        if quantile is not None:
            assert vmin is None and vmax is None, "ERROR: arguments 'quantile' and 'vmin', 'vmax' cannot be used together"

        if quantile is not None:
            vmin, vmax = np.nanquantile(data, quantile)

        plt.figure()
        data.plot.imshow(cmap=cmap, vmin=vmin, vmax=vmax)
        self.plot_AOI(**kwargs)
        self.plot_POI(**kwargs)
        if self.is_ra(data):
            plt.xlabel('Range')
            plt.ylabel('Azimuth')
        plt.title(caption)

#     def get_adi_threshold(self, threshold):
#         """
#         Vectorize Amplitude Dispersion Index (ADI) raster values selected using the specified threshold.
#         """
#         import numpy as np
#         import dask
#         import pandas as pd
#         import geopandas as gpd
# 
#         def adi_block(ys, xs):
#             from scipy.interpolate import griddata
#             # we can calculate more accurate later
#             dy = dx = 10
#             trans_inv_block = trans_inv.sel(y=slice(min(ys)-dy,max(ys)+dy), x=slice(min(xs)-dx,max(xs)+dx))
#             lt_block = trans_inv_block.lt.compute(n_workers=1).data.ravel()
#             ll_block = trans_inv_block.ll.compute(n_workers=1).data.ravel()
#             block_y, block_x = np.meshgrid(trans_inv_block.y.data, trans_inv_block.x.data)
#             points = np.column_stack([block_y.ravel(), block_x.ravel()])
#             # following NetCDF indices 0.5,1.5,...
#             adi_block = adi.sel(y=slice(min(ys),max(ys)+1), x=slice(min(xs),max(xs)+1))
#             adi_block_value = adi_block.compute(n_workers=1).data.ravel()
#             adi_block_mask = adi_block_value<=threshold
#             adi_block_value = adi_block_value[adi_block_mask]
#             adi_block_y, adi_block_x = np.meshgrid(adi_block.y, adi_block.x)
#             adi_block_y = adi_block_y.ravel()[adi_block_mask]
#             adi_block_x = adi_block_x.ravel()[adi_block_mask]
#             # interpolate geographic coordinates, coarsen=2 grid is required for the best accuracy
#             grid_lt = griddata(points, lt_block, (adi_block_y, adi_block_x), method='linear').astype(np.float32)
#             grid_ll = griddata(points, ll_block, (adi_block_y, adi_block_x), method='linear').astype(np.float32)
#             # return geographic coordinates and values
#             return np.column_stack([grid_lt, grid_ll, adi_block_value])
#     
#         # data grid and transform table
#         adi = self.get_adi()
#         trans_inv = self.get_trans_inv()
#     
#         # split to equal chunks and rest
#         ys_blocks = np.array_split(np.arange(adi.y.size), np.arange(0, adi.y.size, self.chunksize)[1:])
#         xs_blocks = np.array_split(np.arange(adi.x.size), np.arange(0, adi.x.size, self.chunksize)[1:])
#         # arrays size is unknown so we cannot construct dask array
#         blocks = []
#         for ys_block in ys_blocks:
#             for xs_block in xs_blocks:
#                 block = dask.delayed(adi_block)(ys_block, xs_block)
#                 blocks.append(block)
#                 del block
#     
#         # materialize the result as a set of numpy arrays
#         tqdm_dask(model := dask.persist(blocks), desc='Amplitude Dispersion Index (ADI) Threshold')
#         del blocks
#         # the result is already calculated and compute() returns the result immediately
#         model = np.concatenate(dask.compute(model)[0][0])
#         # convert to geopandas object
#         columns = {'adi': model[:,2], 'geometry': gpd.points_from_xy(model[:,1], model[:,0])}
#         df = gpd.GeoDataFrame(columns, crs="EPSG:4326")
#         del columns
#         return df

#     sbas.plot_amplitudes(dates=sbas.df.index[:8], intensity=True, quantile=[0.01, 0.99],
#                         func=lambda data: data.sel(y=slice(920,960), x=slice(4500,4550)),
#                         marker='x', marker_size=200, POI=sbas.geocode(POI))
#     #AOI=sbas.geocode(AOI.buffer(-0.001))
    def plot_amplitudes(self, dates=None, data='auto', norm='auto', func=None, intensity=False,
                       caption='auto', cmap='gray', cols=4, size=4, nbins=5, aspect=1.2, y=1.05,
                       quantile=None, vmin=None, vmax=None, symmetrical=False, **kwargs):
        import numpy as np
        import pandas as pd
        import matplotlib.pyplot as plt
        import types

        if isinstance(data, str) and data == 'auto':
            # open SLC data as real amplitudes
            #data = np.abs(self.open_data(dates=dates))
            # magick scale for better plots readability
            scale = np.sqrt(2.5e-07) if intensity else 2.5e-07
            data = np.abs(self.open_data(dates=dates, scale=scale))
            if intensity:
                data = np.square(data)
        elif 'stack' in data.dims and isinstance(data.coords['stack'].to_index(), pd.MultiIndex):
            data = data.unstack('stack')

        if func is not None:
            data = func(data)

        if isinstance(norm, str) and norm == 'auto':
            # normilize SLC grids using average
            stack_average = data.mean(['y','x'])
            norm_multiplier = stack_average.mean(dim='date') / stack_average
            #print ('norm_multiplier', norm_multiplier.values)
            data = norm_multiplier * data
        elif norm is not None:
            data = norm * data

        if isinstance(caption, str) and caption == 'auto':
            caption = 'SLC Intensity' if intensity else 'SLC Amplitude'

        if quantile is not None:
            assert vmin is None and vmax is None, "ERROR: arguments 'quantile' and 'vmin', 'vmax' cannot be used together"

        if quantile is not None:
            vmin, vmax = np.nanquantile(data, quantile)

        # define symmetrical boundaries
        if symmetrical is True and vmax > 0:
            minmax = max(abs(vmin), vmax)
            vmin = -minmax
            vmax =  minmax

        # multi-plots ineffective for linked lazy data
        fg = data.plot.imshow(
            col='date',
            col_wrap=cols, size=size, aspect=aspect,
            vmin=vmin, vmax=vmax, cmap=cmap,
            interpolation='none' # Disable interpolation
        )
        if self.is_ra(data):
            fg.set_axis_labels('Range', 'Azimuth')
        fg.set_ticks(max_xticks=nbins, max_yticks=nbins)
        fg.fig.suptitle(caption, y=y)

        self.plots_AOI(fg, **kwargs)
        self.plots_POI(fg, **kwargs)
