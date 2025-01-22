# ----------------------------------------------------------------------------
# PyGMTSAR
# 
# This file is part of the PyGMTSAR project: https://github.com/mobigroup/gmtsar
# 
# Copyright (c) 2023, Alexey Pechnikov
# 
# Licensed under the BSD 3-Clause License (see LICENSE for details)
# ----------------------------------------------------------------------------
from .Stack_topo import Stack_topo
from .tqdm_dask import tqdm_dask
from .PRM import PRM
from .utils import utils

class Stack_phasediff(Stack_topo):

    def compute_interferogram(self, pairs, name, subswath=None, weight=None, topo=None, phase=None, method=None,
                              resolution=None, wavelength=None, psize=None, coarsen=None, real=None,
                              stack=None, queue=None, timeout=None,
                              skip_exist=False, joblib_backend=None, debug=False):
        import xarray as xr
        import numpy as np
        import dask
        # cleanup unused resources before start
        import gc; gc.collect()
    
        if not skip_exist:
            # delete stack files if exist
            self.delete_stack(name)
    
        # define anti-aliasing filter for the specified output resolution
        if wavelength is None:
            wavelength = resolution

        if isinstance(weight, str) and weight == 'auto':
            weight = self.psfunction()
        elif weight is not None:
            weight = weight.astype(np.float32).chunk(-1 if weight.chunks is None else weight.chunks)

        if queue is None:
            queue = self.netcdf_queue
        if queue is None:
            # process all the pairs in a single operation
            queue = len(pairs)
    
        # decimate the 1:4 multilooking grids to specified resolution
        if resolution is not None:
            decimator = self.decimator(resolution=resolution, grid=coarsen, debug=debug)
        else:
            decimator = None
        
        # Applying iterative processing to prevent Dask scheduler deadlocks.
        counter = 0
        digits = len(str(len(pairs)))
        # Splitting all the pairs into chunks, each containing approximately queue pairs.
        #n_chunks = len(pairs) // queue if len(pairs) >= queue else 1
        if len(pairs) > queue:
            chunks = [pairs[i:i + queue] for i in range(0, len(pairs), queue)]
            n_chunks = len(chunks)
        else:
            chunks = [pairs]
            n_chunks = 1
        #for chunk in np.array_split(pairs, n_chunks):
        for chunk in chunks:
            #print (f'Interferogram pairs: {len(pairs)}')
            chunk, dates = self.get_pairs(chunk, dates=True)
            # load Sentinel-1 data
            data = self.open_data(dates, subswath=subswath, debug=debug)
            if weight is not None:
                data = data.reindex_like(weight, fill_value=np.nan)
            intensity = np.square(np.abs(data))
            # Gaussian filtering 200m cut-off wavelength with optional range multilooking on Sentinel-1 amplitudes
            intensity_look = self.multilooking(intensity, wavelength=wavelength, coarsen=coarsen, debug=debug)
            del intensity
            # calculate phase difference with topography correction
            phasediff = self.phasediff(chunk, data, topo=topo, phase=phase, method=method, joblib_backend=joblib_backend, debug=debug)
            del data
            # Gaussian filtering 200m cut-off wavelength with optional range multilooking
            phasediff_look = self.multilooking(phasediff, weight=weight,
                                               wavelength=wavelength, coarsen=coarsen, debug=debug)
            del phasediff
            # correlation with optional range decimation
            corr_look = self.correlation(phasediff_look, intensity_look, debug=debug)
            del intensity_look
            if psize is not None:
                # Goldstein filter in psize pixel patch size on square grid cells produced using 1:4 range multilooking
                phasediff_look_goldstein = self.goldstein(phasediff_look, corr_look, psize, debug=debug)
                del phasediff_look
                # convert complex phase difference to interferogram
                #intf_look = self.interferogram(phasediff_look_goldstein, debug=debug)
                phasediff_look = phasediff_look_goldstein
                del phasediff_look_goldstein

            # filter out not valid pixels
            if weight is not None:
                weight_look = self.multilooking(weight, wavelength=None, coarsen=coarsen, debug=debug)
                phasediff_look = phasediff_look.where(np.isfinite(weight_look))
                corr_look = corr_look.where(np.isfinite(weight_look))
                del weight_look
                
            if real:
                # convert complex phase difference to interferogram
                intf_look = self.interferogram(phasediff_look, debug=debug)
            else:
                # output complex phase
                intf_look = phasediff_look
            del phasediff_look
    
            # compute together because correlation depends on phase, and filtered phase depends on correlation.
            #tqdm_dask(result := dask.persist(decimator(corr15m), decimator(intf15m)), desc='Compute Phase and Correlation')
            # unpack results for a single interferogram
            #corr90m, intf90m = [grid[0] for grid in result]
            # anti-aliasing filter for the output resolution is applied above
            if decimator is not None:
                intf_dec = decimator(intf_look)
                corr_dec = decimator(corr_look)
                out = xr.merge([intf_dec, corr_dec])
                del intf_dec, corr_dec
            else:
                out = xr.merge([intf_look, corr_look])
            del corr_look, intf_look

            if isinstance(stack, xr.DataArray):
                out = out.interp(y=stack.y, x=stack.x, method='nearest')

            caption = f'Saving Interferogram {(counter+1):0{digits}}...{(counter+len(chunk)):0{digits}} from {len(pairs)}'
            self.save_stack(out, name, caption=caption, queue=queue, timeout=timeout)
            counter += len(chunk)
            del out, chunk, dates

    # single-look interferogram processing has a limited set of arguments
    # resolution and coarsen are not applicable here
    def compute_interferogram_singlelook(self, pairs, name, subswath=None, weight=None, topo='auto', phase=None,
                                         wavelength=None, method='nearest', psize=None, real=True,
                                         stack=None, queue=16, timeout=None,
                                         skip_exist=False, joblib_backend=None, debug=False):
        self.compute_interferogram(pairs, name, subswath=subswath, weight=weight, topo=topo, phase=phase, method=method,
                                   wavelength=wavelength, psize=psize, real=real,
                                   stack=stack, queue=queue, timeout=timeout,
                                   skip_exist=skip_exist, joblib_backend=joblib_backend, debug=debug)

    # Goldstein filter requires square grid cells means 1:4 range multilooking.
    # For multilooking interferogram we can use square grid always using coarsen = (1,4)
    def compute_interferogram_multilook(self, pairs, name, subswath=None, weight=None, topo='auto', phase=None,
                                        resolution=None, wavelength=None, method='nearest', psize=None, coarsen=(1,4), real=True,
                                        stack=None, queue=16, timeout=None,
                                        skip_exist=False, joblib_backend=None, debug=False):
        self.compute_interferogram(pairs, name, subswath=subswath, weight=weight, topo=topo, phase=phase, method=method,
                                   resolution=resolution,  wavelength=wavelength, psize=psize, coarsen=coarsen, real=real,
                                   stack=stack, queue=queue, timeout=timeout,
                                   skip_exist=skip_exist, joblib_backend=joblib_backend, debug=debug)

    @staticmethod
    def interferogram(phase, debug=False):
        import numpy as np

        if debug:
            print ('DEBUG: interferogram')

        if np.issubdtype(phase.dtype, np.complexfloating):
            return np.arctan2(phase.imag, phase.real).rename('phase')
        return phase

#     @staticmethod
#     def correlation(I1, I2, amp):
#         import xarray as xr
#         import numpy as np
#         # constant from GMTSAR code
#         thresh = 5.e-21
#         i = I1 * I2
#         corr = xr.where(i > 0, amp / np.sqrt(i), 0)
#         corr = xr.where(corr < 0, 0, corr)
#         corr = xr.where(corr > 1, 1, corr)
#         # mask too low amplitude areas as invalid
#         # amp1 and amp2 chunks are high for SLC, amp has normal chunks for NetCDF
#         return xr.where(i >= thresh, corr, np.nan).chunk(a.chunksizes).rename('phase')

    def correlation(self, phase, intensity, debug=False):
        """
        Example:
        data_200m = stack.multilooking(np.abs(sbas.open_data()), wavelength=200, coarsen=(4,16))
        intf2_200m = stack.multilooking(intf2, wavelength=200, coarsen=(4,16))
        stack.correlation(intf2_200m, data_200m)

        Note:
        Multiple interferograms require the same data grids, allowing us to speed up the calculation
        by saving filtered data to a disk file.
        """
        import pandas as pd
        import dask
        import xarray as xr
        import numpy as np

        if debug:
            print ('DEBUG: correlation')

        # convert pairs (list, array, dataframe) to 2D numpy array
        pairs, dates = self.get_pairs(phase, dates=True)
        pairs = pairs[['ref', 'rep']].astype(str).values

        # check correctness for user-defined data arguments
        assert np.issubdtype(phase.dtype, np.complexfloating), 'ERROR: Phase should be complex-valued data.'
        assert not np.issubdtype(intensity.dtype, np.complexfloating), 'ERROR: Intensity cannot be complex-valued data.'

        stack = []
        for stack_idx, pair in enumerate(pairs):
            date1, date2 = pair
            # calculate correlation
            corr = np.abs(phase.sel(pair=' '.join(pair)) / np.sqrt(intensity.sel(date=date1) * intensity.sel(date=date2)))
            corr = xr.where(corr < 0, 0, corr)
            corr = xr.where(corr > 1, 1, corr)
            # add to stack
            stack.append(corr)
            del corr

        return xr.concat(stack, dim='pair').rename('correlation')

#     def phasediff(self, pairs, data='auto', topo='auto', method='cubic', debug=False):
#         import pandas as pd
#         import dask
#         import xarray as xr
#         import numpy as np
#         import warnings
#         # suppress Dask warning "RuntimeWarning: invalid value encountered in divide"
#         warnings.filterwarnings('ignore')
#         warnings.filterwarnings('ignore', module='dask')
#         warnings.filterwarnings('ignore', module='dask.core')
# 
#         if debug:
#             print ('DEBUG: phasediff')
# 
#         # convert pairs (list, array, dataframe) to 2D numpy array
#         pairs, dates = self.get_pairs(pairs, dates=True)
#         pairs = pairs[['ref', 'rep']].astype(str).values
# 
#         if isinstance(topo, str) and topo == 'auto':
#             topo = self.get_topo()
# 
#         # calculate the combined earth curvature and topography correction
#         def calc_drho(rho, topo, earth_radius, height, b, alpha, Bx):
#             sina = np.sin(alpha)
#             cosa = np.cos(alpha)
#             c = earth_radius + height
#             # compute the look angle using equation (C26) in Appendix C
#             # GMTSAR uses long double here
#             #ret = earth_radius + topo.astype(np.longdouble)
#             ret = earth_radius + topo
#             cost = ((rho**2 + c**2 - ret**2) / (2. * rho * c))
#             #if (cost >= 1.)
#             #    die("calc_drho", "cost >= 0");
#             sint = np.sqrt(1. - cost**2)
#             # Compute the offset effect from non-parallel orbit
#             term1 = rho**2 + b**2 - 2 * rho * b * (sint * cosa - cost * sina) - Bx**2
#             drho = -rho + np.sqrt(term1)
#             del term1, sint, cost, ret, c, cosa, sina
#             return drho
# 
#         def block_phasediff(stack_idx, date1, date2, ylim, xlim):
#             # use outer variables date, stack_prm
#             # disable "distributed.utils_perf - WARNING - full garbage collections ..."
#             from dask.distributed import utils_perf
#             utils_perf.disable_gc_diagnosis()
#             import warnings
#             # suppress Dask warning "RuntimeWarning: invalid value encountered in divide"
#             warnings.filterwarnings('ignore')
#             warnings.filterwarnings('ignore', module='dask')
#             warnings.filterwarnings('ignore', module='dask.core')
# 
#             # unpack input stacks
#             prm1,  prm2  = stack_prm[stack_idx]
#             #data1, data2 = stack_data[stack_idx]
#             data1 = data.sel(date=date1)
#             data2 = data.sel(date=date2)
# 
#             # convert indices 0.5, 1.5,... to 0,1,... for easy calculations
#             block_data1 = data1.isel(y=slice(ylim[0], ylim[1]), x=slice(xlim[0], xlim[1])).compute(n_workers=1)
#             block_data2 = data2.isel(y=slice(ylim[0], ylim[1]), x=slice(xlim[0], xlim[1])).compute(n_workers=1)
#             del data1, data2
# 
#             if abs(block_data1).sum() == 0:
#                 intf = np.nan * xr.zeros_like(block_data1)
#                 del block_data1, block_data2
#                 return intf
# 
#             ys = block_data1.y.astype(int)
#             xs = block_data1.x.astype(int)
# 
#             block_data1 = block_data1.assign_coords(y=ys, x=xs)
#             block_data2 = block_data2.assign_coords(y=ys, x=xs)
# 
#             # use outer variables topo, data1, data2, prm1, prm2
#             # build topo block
#             dy, dx = topo.y.diff('y').item(0), topo.x.diff('x').item(0)
#             if dy == 1 and dx == 1:
#                 # topography is already in the original resolution
#                 block_topo = topo.isel(y=slice(ylim[0], ylim[1]), x=slice(xlim[0], xlim[1]))\
#                             .compute(n_workers=1)\
#                             .fillna(0)\
#                             .assign_coords(y=ys, x=xs)
#             else:
#                 # topography resolution is different, interpolation with extrapolation required
#                 # convert indices 0.5, 1.5,... to 0,1,... for easy calculations
#                 # fill NaNs by zero because typically DEM is missed outside of land areas
#                 block_topo = topo.sel(y=slice(ys[0]-3*dy, ys[-1]+3*dy), x=slice(xs[0]-3*dx, xs[-1]+3*dx))\
#                             .compute(n_workers=1)\
#                             .fillna(0)\
#                             .interp({'y': block_data1.y, 'x': block_data1.x}, method=method, kwargs={'fill_value': 'extrapolate'})\
#                             .assign_coords(y=ys, x=xs)
#             # set dimensions
#             xdim = prm1.get('num_rng_bins')
#             ydim = prm1.get('num_patches') * prm1.get('num_valid_az')
# 
#             # set heights
#             htc = prm1.get('SC_height')
#             ht0 = prm1.get('SC_height_start')
#             htf = prm1.get('SC_height_end')
# 
#             # compute the time span and the time spacing
#             tspan = 86400 * abs(prm2.get('SC_clock_stop') - prm2.get('SC_clock_start'))
#             assert (tspan >= 0.01) and (prm2.get('PRF') >= 0.01), 'Check sc_clock_start, sc_clock_end, or PRF'
# 
#             from scipy import constants
#             # setup the default parameters
#             # constant from GMTSAR code for consistency
#             #SOL = 299792456.0
#             drange = constants.speed_of_light / (2 * prm2.get('rng_samp_rate'))
#             #drange = SOL / (2 * prm2.get('rng_samp_rate'))
#             alpha = prm2.get('alpha_start') * np.pi / 180
#             cnst = -4 * np.pi / prm2.get('radar_wavelength')
# 
#             # calculate initial baselines
#             Bh0 = prm2.get('baseline_start') * np.cos(prm2.get('alpha_start') * np.pi / 180)
#             Bv0 = prm2.get('baseline_start') * np.sin(prm2.get('alpha_start') * np.pi / 180)
#             Bhf = prm2.get('baseline_end')   * np.cos(prm2.get('alpha_end')   * np.pi / 180)
#             Bvf = prm2.get('baseline_end')   * np.sin(prm2.get('alpha_end')   * np.pi / 180)
#             Bx0 = prm2.get('B_offset_start')
#             Bxf = prm2.get('B_offset_end')
# 
#             # first case is quadratic baseline model, second case is default linear model
#             if prm2.get('baseline_center') != 0 or prm2.get('alpha_center') != 0 or prm2.get('B_offset_center') != 0:
#                 Bhc = prm2.get('baseline_center') * np.cos(prm2.get('alpha_center') * np.pi / 180)
#                 Bvc = prm2.get('baseline_center') * np.sin(prm2.get('alpha_center') * np.pi / 180)
#                 Bxc = prm2.get('B_offset_center')
# 
#                 dBh = (-3 * Bh0 + 4 * Bhc - Bhf) / tspan
#                 dBv = (-3 * Bv0 + 4 * Bvc - Bvf) / tspan
#                 ddBh = (2 * Bh0 - 4 * Bhc + 2 * Bhf) / (tspan * tspan)
#                 ddBv = (2 * Bv0 - 4 * Bvc + 2 * Bvf) / (tspan * tspan)
# 
#                 dBx = (-3 * Bx0 + 4 * Bxc - Bxf) / tspan
#                 ddBx = (2 * Bx0 - 4 * Bxc + 2 * Bxf) / (tspan * tspan)
#             else:
#                 dBh = (Bhf - Bh0) / tspan
#                 dBv = (Bvf - Bv0) / tspan
#                 dBx = (Bxf - Bx0) / tspan
#                 ddBh = ddBv = ddBx = 0
# 
#             # calculate height increment
#             dht = (-3 * ht0 + 4 * htc - htf) / tspan
#             ddht = (2 * ht0 - 4 * htc + 2 * htf) / (tspan * tspan)
# 
#             # multiply xr.ones_like(topo) for correct broadcasting
#             near_range = xr.ones_like(block_topo)*(prm1.get('near_range') + \
#                 block_topo.x * (1 + prm1.get('stretch_r')) * drange) + \
#                 xr.ones_like(block_topo)*(block_topo.y * prm1.get('a_stretch_r') * drange)
# 
#             # calculate the change in baseline and height along the frame if topoflag is on
#             time = block_topo.y * tspan / (ydim - 1)        
#             Bh = Bh0 + dBh * time + ddBh * time**2
#             Bv = Bv0 + dBv * time + ddBv * time**2
#             Bx = Bx0 + dBx * time + ddBx * time**2
#             B = np.sqrt(Bh * Bh + Bv * Bv)
#             alpha = np.arctan2(Bv, Bh)
#             height = ht0 + dht * time + ddht * time**2
# 
#             # calculate the combined earth curvature and topography correction
#             drho = calc_drho(near_range, block_topo, prm1.get('earth_radius'), height, B, alpha, Bx)
# 
#             # make topographic and model phase corrections
#             # GMTSAR uses float32 complex operations with precision loss
#             #phase_shift = np.exp(1j * (cnst * drho).astype(np.float32))
#             phase_shift = np.exp(1j * (cnst * drho))
#             del block_topo, near_range, drho, height, B, alpha, Bx, Bv, Bh, time
# 
#             # calculate phase difference
#             intf = block_data1 * phase_shift * np.conj(block_data2)
#             del block_data1, block_data2, phase_shift
#             return intf.astype(np.complex64)
# 
#         if isinstance(data, str) and data == 'auto':
#             # open datafiles required for all the pairs
#             data = self.open_data(dates)
# 
#         # define blocks
#         chunks = data.chunks
#         ychunks,xchunks = chunks[1], chunks[2]
#         ychunks = np.concatenate([[0], np.cumsum(ychunks)])
#         xchunks = np.concatenate([[0], np.cumsum(xchunks)])
#         ylims = [(y1, y2) for y1, y2 in zip(ychunks, ychunks[1:])]
#         xlims = [(x1, x2) for x1, x2 in zip(xchunks, xchunks[1:])]
#         #print ('ylims', ylims)
#         #print ('xlims', xlims)
# 
#         stack_prm  = []
#         stack_data = []
#         stack = []
#         for stack_idx, pair in enumerate(pairs):
#             date1, date2 = pair
# 
#             # prepare for delayed stack processing
#             prm1 = self.PRM(date1)
#             prm2 = self.PRM(date2)
#             # it does not work because attributes are the same for all the grids
#             #prm1 = PRM.from_str(data1.prm)
#             #prm2 = PRM.from_str(data2.prm)
#             # directory and filename required for SAT_... tools to locate LED file
#             #prm1.filename = os.path.join(self.basedir, prm1.get('led_file'))
#             #prm2.filename = os.path.join(self.basedir, prm2.get('led_file'))
#             #print ('prm1.filename', prm1.filename)
# 
#             # update and add required parameters
#             prm2.set(prm1.SAT_baseline(prm2, tail=9)).fix_aligned()
#             prm1.set(prm1.SAT_baseline(prm1).sel('SC_height','SC_height_start','SC_height_end')).fix_aligned()
#             stack_prm.append((prm1, prm2))
#             #print ('.', end='')
# 
#             # check the grids
#             #assert prm1.get('num_rng_bins') == prm2.get('num_rng_bins'), 'The dimensions of range do not match'
#             #assert prm1.get('num_patches') * prm1.get('num_valid_az') == prm2.get('num_patches') * prm2.get('num_valid_az'), \
#             #    'The dimensions of azimuth do not match'
# 
#             if topo is None:
#                 # calculation is straightforward and does not require delayed wrappers
#                 intf = (data.sel(date=date1) * np.conj(data.sel(date=date2)))
#             else:
#                 # split to equal chunks and rest
#                 #ys_blocks = np.array_split(data[0].y, np.arange(0,data.y.size, self.chunksize)[1:])
#                 #xs_blocks = np.array_split(data[0].x, np.arange(0,data.x.size, self.chunksize)[1:])
#                 #print ('ys_blocks.size', len(ys_blocks), 'xs_blocks.size', len(xs_blocks))
#                 blocks_total = []
#                 for ylim in ylims:
#                     blocks = []
#                     for xlim in xlims:
#                         block = dask.array.from_delayed(dask.delayed(block_phasediff)(stack_idx, date1, date2, ylim, xlim),
#                                                         shape=((ylim[1]-ylim[0]), (xlim[1]-xlim[0])), dtype=np.complex64)
#                         blocks.append(block)
#                         del block
#                     blocks_total.append(blocks)
#                     del blocks
#                 intf = xr.DataArray(dask.array.block(blocks_total), coords={'y': data.y, 'x': data.x})
#                 del blocks_total
# 
#             # add to stack
#             stack.append(intf)
#             # cleanup
#             del intf, prm1, prm2
# 
#         coord_pair = [' '.join(pair) for pair in pairs]
#         coord_ref = xr.DataArray(pd.to_datetime(pairs[:,0]), coords={'pair': coord_pair})
#         coord_rep = xr.DataArray(pd.to_datetime(pairs[:,1]), coords={'pair': coord_pair})
# 
#         return xr.concat(stack, dim='pair').assign_coords(ref=coord_ref, rep=coord_rep, pair=coord_pair).rename('phasediff')

    def phasediff(self, pairs, data='auto', topo='auto', phase=None, method='nearest', joblib_backend=None, debug=False):
        #import dask
        import dask.array as da
        import xarray as xr
        import numpy as np
        import pandas as pd

        if debug:
            print ('DEBUG: phasediff')
        
        if joblib_backend is None and debug:
            joblib_backend = 'sequential'

        # convert pairs (list, array, dataframe) to 2D numpy array
        pairs, dates = self.get_pairs(pairs, dates=True)
        pairs = pairs[['ref', 'rep']].astype(str).values

        if isinstance(data, str) and data == 'auto':
            # open datafiles required for all the pairs
            data = self.open_data(dates)

        # interpret the topo argument as topography, otherwise, use it as topography phase
        if isinstance(topo, str) and topo == 'auto':
            topo = self.get_topo()

        if (isinstance(topo, xr.DataArray) and topo.name=='topo'):
            topo_grid = utils.interp2d_like(topo, data, method=method, kwargs={'fill_value': 'extrapolate'})
            phase_topo = self.topo_phase(pairs, topo_grid, grid=data, method=method)
            del topo_grid
        elif (isinstance(topo, xr.DataArray) and topo.name=='phase'):
            phase_topo = topo
        else:
            # use zero topography grid
            coords = {key: value for key, value in data[0].coords.items() if key != 'date'}
            notopo = xr.DataArray(da.zeros_like(data[0], dtype=np.float32), coords=coords)
            phase_topo = self.topo_phase(pairs, notopo, method=method)
            del notopo

        if phase is not None:
            phase_real = xr.concat([utils.interp2d_like(phase2d, data, method=method,
                                    kwargs={'fill_value': 'extrapolate'}) for phase2d in phase], dim='pair')
        else:
            phase_real = 0
            #phase_real = len(pairs)*[0]

        # calculate phase difference
        data1 = data.sel(date=pairs[:,0]).drop_vars('date').rename({'date': 'pair'})
        data2 = data.sel(date=pairs[:,1]).drop_vars('date').rename({'date': 'pair'})
        out = (data1 * phase_topo * np.exp(-1j * phase_real) * da.conj(data2)).astype(np.complex64).rename('phase')
        del phase_topo, phase_real, data1, data2

        # # calculate phase difference
        # phase_dask = da.stack([(data.sel(date=pair[0]).drop_vars('date') \
        #          * phase_topo[idx] * np.exp(-1j * phase_real[idx]) \
        #          * da.conj(data.sel(date=pair[1]).drop_vars('date'))) for idx, pair in enumerate(pairs)], axis=0)
        # out = xr.DataArray(phase_dask, coords=phase_topo.coords)
        # del phase_topo, phase_real, phase_dask

        if not isinstance(topo, xr.DataArray):
            # append coordinates which usually added from topo phase dataarray
            coord_pair = [' '.join(pair) for pair in pairs]
            coord_ref = xr.DataArray(pd.to_datetime(pairs[:,0]), coords={'pair': coord_pair})
            coord_rep = xr.DataArray(pd.to_datetime(pairs[:,1]), coords={'pair': coord_pair})
            return out.assign_coords(ref=coord_ref, rep=coord_rep, pair=coord_pair)
        return out

    def goldstein(self, phase, corr, psize=32, debug=False):
        import xarray as xr
        import numpy as np
        import dask
        import warnings
        # suppress Dask warning "RuntimeWarning: invalid value encountered in divide"
        warnings.filterwarnings('ignore')
        warnings.filterwarnings('ignore', module='dask')
        warnings.filterwarnings('ignore', module='dask.core')

        if debug:
            print ('DEBUG: goldstein')

        if psize is None:
            # miss the processing
            return phase
        
        if not isinstance(psize, (list, tuple)):
            psize = (psize, psize)

        def apply_pspec(data, alpha):
            # NaN is allowed value
            assert not(alpha < 0), f'Invalid parameter value {alpha} < 0'
            wgt = np.power(np.abs(data)**2, alpha / 2)
            data = wgt * data
            return data

        def make_wgt(psize):
            nyp, nxp = psize
            # Create arrays of horizontal and vertical weights
            wx = 1.0 - np.abs(np.arange(nxp // 2) - (nxp / 2.0 - 1.0)) / (nxp / 2.0 - 1.0)
            wy = 1.0 - np.abs(np.arange(nyp // 2) - (nyp / 2.0 - 1.0)) / (nyp / 2.0 - 1.0)
            # Compute the outer product of wx and wy to create the top-left quadrant of the weight matrix
            quadrant = np.outer(wy, wx)
            # Create a full weight matrix by mirroring the quadrant along both axes
            wgt = np.block([[quadrant, np.flip(quadrant, axis=1)],
                            [np.flip(quadrant, axis=0), np.flip(np.flip(quadrant, axis=0), axis=1)]])
            return wgt

        def patch_goldstein_filter(data, corr, wgt, psize):
            """
            Apply the Goldstein adaptive filter to the given data.

            Args:
                data: 2D numpy array of complex values representing the data to be filtered.
                corr: 2D numpy array of correlation values. Must have the same shape as `data`.

            Returns:
                2D numpy array of filtered data.
            """
            # Calculate alpha
            alpha = 1 - (wgt * corr).sum() / wgt.sum()
            data = np.fft.fft2(data, s=psize)
            data = apply_pspec(data, alpha)
            data = np.fft.ifft2(data, s=psize)
            return wgt * data

        def apply_goldstein_filter(data, corr, psize, wgt_matrix):
            # Create an empty array for the output
            out = np.zeros(data.shape, dtype=np.complex64)
            # ignore processing for empty chunks 
            if np.all(np.isnan(data)):
                return out
            # Create the weight matrix
            #wgt_matrix = make_wgt(psize)
            # Iterate over windows of the data
            for i in range(0, data.shape[0] - psize[0], psize[0] // 2):
                for j in range(0, data.shape[1] - psize[1], psize[1] // 2):
                    # Create proocessing windows
                    data_window = data[i:i+psize[0], j:j+psize[1]]
                    corr_window = corr[i:i+psize[0], j:j+psize[1]]
                    wgt_window = wgt_matrix[:data_window.shape[0],:data_window.shape[1]]
                    # Apply the filter to the window
                    filtered_window = patch_goldstein_filter(data_window, corr_window, wgt_window, psize)
                    # Add the result to the output array
                    slice_i = slice(i, min(i + psize[0], out.shape[0]))
                    slice_j = slice(j, min(j + psize[1], out.shape[1]))
                    out[slice_i, slice_j] += filtered_window[:slice_i.stop - slice_i.start, :slice_j.stop - slice_j.start]
            return out

        assert phase.shape == corr.shape, f'ERROR: phase and correlation variables have different shape \
                                          ({phase.shape} vs {corr.shape})'
#         spacing = self.get_spacing(phase)
#         #assert np.round(spacing[0]/spacing[1]) == 1, f'ERROR: grid cells should be almost square: {spacing}'
#         if not np.round(spacing[0]/spacing[1]) == 1:
#             print (f'NOTE: grid cells are not close to square as expected: {spacing}')
#         
        if len(phase.dims) == 2:
            stackvar = None
        else:
            stackvar = phase.dims[0]
    
        stack =[]
        for ind in range(len(phase) if stackvar is not None else 1):
            # Apply function with overlap; psize//2 overlap is not enough (some empty lines produced)
            # use complex data and real correlation
            # fill NaN values in correlation by zeroes to prevent empty output blocks
            block = dask.array.map_overlap(apply_goldstein_filter,
                                           (phase[ind] if stackvar is not None else phase).fillna(0).data,
                                           (corr[ind]  if stackvar is not None else corr ).fillna(0).data,
                                           depth=(psize[0] // 2 + 2, psize[1] // 2 + 2),
                                           dtype=np.complex64, 
                                           meta=np.array(()),
                                           psize=psize,
                                           wgt_matrix = make_wgt(psize))
            # Calculate the phase
            stack.append(block)
            del block

        if stackvar is not None:
            ds = xr.DataArray(dask.array.stack(stack), coords=phase.coords)
        else:
            ds = xr.DataArray(stack[0], coords=phase.coords)
        del stack
        # replace zeros produces in NODATA areas
        return ds.where(ds).rename('phase')

    def plot_phase(self, data, caption='Phase, [rad]',
                   quantile=None, vmin=None, vmax=None, symmetrical=False,
                   cmap='turbo', aspect=None, **kwargs):
        import numpy as np
        import pandas as pd
        import matplotlib.pyplot as plt

        if 'stack' in data.dims and isinstance(data.coords['stack'].to_index(), pd.MultiIndex):
            data = data.unstack('stack')

        if quantile is not None:
            assert vmin is None and vmax is None, "ERROR: arguments 'quantile' and 'vmin', 'vmax' cannot be used together"

        if quantile is not None:
            vmin, vmax = np.nanquantile(data, quantile)

        # define symmetrical boundaries
        if symmetrical is True and vmax > 0:
            minmax = max(abs(vmin), vmax)
            vmin = -minmax
            vmax =  minmax

        plt.figure()
        data.plot.imshow(vmin=vmin, vmax=vmax, cmap=cmap)
        self.plot_AOI(**kwargs)
        self.plot_POI(**kwargs)
        if aspect is not None:
            plt.gca().set_aspect(aspect)
        plt.title(caption)

    def plot_phases(self, data, caption='Phase, [rad]', cols=4, size=4, nbins=5, aspect=1.2, y=1.05,
                    quantile=None, vmin=None, vmax=None, symmetrical=False, **kwargs):
        import numpy as np
        import pandas as pd
        import matplotlib.pyplot as plt

        if 'stack' in data.dims and isinstance(data.coords['stack'].to_index(), pd.MultiIndex):
            data = data.unstack('stack')

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
            col='pair',
            col_wrap=cols, size=size, aspect=aspect,
            vmin=vmin, vmax=vmax, cmap='turbo'
        )
        if self.is_ra(data):
            fg.set_axis_labels('Range', 'Azimuth')
        fg.set_ticks(max_xticks=nbins, max_yticks=nbins)
        fg.fig.suptitle(caption, y=y)
        
        self.plots_AOI(fg, **kwargs)
        self.plots_POI(fg, **kwargs)

    def plot_interferogram(self, data, caption='Phase, [rad]', cmap='gist_rainbow_r', aspect=None, **kwargs):
        import numpy as np
        import pandas as pd
        import matplotlib.pyplot as plt

        if 'stack' in data.dims and isinstance(data.coords['stack'].to_index(), pd.MultiIndex):
            data = data.unstack('stack')

        plt.figure()
        data.plot.imshow(vmin=-np.pi, vmax=np.pi, cmap=cmap)
        self.plot_AOI(**kwargs)
        self.plot_POI(**kwargs)
        if aspect is not None:
            plt.gca().set_aspect(aspect)
        plt.title(caption)

    def plot_interferograms(self, data, caption='Phase, [rad]', cols=4, size=4, nbins=5, aspect=1.2, y=1.05, **kwargs):
        import numpy as np
        import pandas as pd
        import matplotlib.pyplot as plt

        if 'stack' in data.dims and isinstance(data.coords['stack'].to_index(), pd.MultiIndex):
            data = data.unstack('stack')

        # multi-plots ineffective for linked lazy data
        fg = self.wrap(data).plot.imshow(
            col='pair',
            col_wrap=cols, size=size, aspect=aspect,
            vmin=-np.pi, vmax=np.pi, cmap='gist_rainbow_r'
        )
        if self.is_ra(data):
            fg.set_axis_labels('Range', 'Azimuth')
        fg.set_ticks(max_xticks=nbins, max_yticks=nbins)
        fg.fig.suptitle(caption, y=y)
        
        self.plots_AOI(fg, **kwargs)
        self.plots_POI(fg, **kwargs)

    def plot_correlation(self, data, caption='Correlation', cmap='gray', aspect=None, **kwargs):
        import pandas as pd
        import matplotlib.pyplot as plt

        if 'stack' in data.dims and isinstance(data.coords['stack'].to_index(), pd.MultiIndex):
            data = data.unstack('stack')

        plt.figure()
        data.plot.imshow(vmin=0, vmax=1, cmap=cmap)
        self.plot_AOI(**kwargs)
        self.plot_POI(**kwargs)
        if aspect is not None:
            plt.gca().set_aspect(aspect)
        plt.title(caption)

    def plot_correlations(self, data, caption='Correlation', cmap='auto', cols=4, size=4, nbins=5, aspect=1.2, y=1.05, **kwargs):
        import pandas as pd
        import matplotlib.pyplot as plt
        import matplotlib.colors as mcolors

        if 'stack' in data.dims and isinstance(data.coords['stack'].to_index(), pd.MultiIndex):
            data = data.unstack('stack')

        if isinstance(cmap, str) and cmap == 'auto':
            cmap = mcolors.LinearSegmentedColormap.from_list(
                name='custom_gray', 
                colors=['black', 'whitesmoke']
            )

        # multi-plots ineffective for linked lazy data
        fg = data.plot.imshow(
            col='pair',
            col_wrap=cols, size=size, aspect=aspect,
            vmin=0, vmax=1, cmap=cmap
        )
        if self.is_ra(data):
            fg.set_axis_labels('Range', 'Azimuth')
        fg.set_ticks(max_xticks=nbins, max_yticks=nbins)
        fg.fig.suptitle(caption, y=y)
        
        self.plots_AOI(fg, **kwargs)
        self.plots_POI(fg, **kwargs)

    def plot_correlation_stack(self, data, threshold=None, caption='Correlation Stack', bins=100, cmap='auto', **kwargs):
        import numpy as np
        import pandas as pd
        import matplotlib.pyplot as plt
        import matplotlib.colors as mcolors

        if 'stack' in data.dims and isinstance(data.coords['stack'].to_index(), pd.MultiIndex):
            data = data.unstack('stack')

        if isinstance(cmap, str) and cmap == 'auto':
            cmap = mcolors.LinearSegmentedColormap.from_list(
                name='custom_gray', 
                colors=['black', 'whitesmoke']
            )
    
        data_flatten = data.values.ravel()
    
        fig, axs = plt.subplots(1, 2)
    
        ax2 = axs[0].twinx()
        axs[0].hist(data_flatten, range=(0, 1), bins=bins, density=False, cumulative=False, color='gray', edgecolor='black', alpha=0.5)
        ax2.hist(data_flatten, range=(0, 1), bins=bins, density=False, cumulative=True, color='orange', edgecolor='black', alpha=0.25)
    
        mean_value = np.nanmean(data_flatten)
        axs[0].axvline(mean_value, color='b', label=f'Average {mean_value:0.3f}')
        median_value = np.nanmedian(data_flatten)
        axs[0].axvline(median_value, color='g', label=f'Median {median_value:0.3f}')
        axs[0].set_xlim([0, 1])
        axs[0].grid()
        axs[0].set_xlabel('Correlation')
        axs[0].set_ylabel('Count')
        ax2.set_ylabel('Cumulative Count', color='orange')
    
        axs[0].set_title('Histogram')
        if threshold is not None:
            data.where(data > threshold).plot.imshow(cmap=cmap, vmin=0, vmax=1, ax=axs[1])
            axs[1].set_title(f'Threshold = {threshold:0.3f}')
            axs[0].axvline(threshold, linestyle='dashed', color='black', label=f'Threshold {threshold:0.3f}')
        else:
            data.where(data).plot.imshow(cmap=cmap, vmin=0, vmax=1, ax=axs[1])
        axs[0].legend()
        self.plot_AOI(ax=axs[1], **kwargs)
        self.plot_POI(ax=axs[1], **kwargs)
        plt.suptitle(caption)
        plt.tight_layout()
