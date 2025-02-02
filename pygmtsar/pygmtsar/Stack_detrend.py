# ----------------------------------------------------------------------------
# PyGMTSAR
# 
# This file is part of the PyGMTSAR project: https://github.com/mobigroup/gmtsar
# 
# Copyright (c) 2021, Alexey Pechnikov
# 
# Licensed under the BSD 3-Clause License (see LICENSE for details)
# ----------------------------------------------------------------------------
from .Stack_unwrap import Stack_unwrap

class Stack_detrend(Stack_unwrap):
# 
#     @staticmethod
#     def regression_linear(data, grid, fit_intercept=True):
#         import numpy as np
#         import xarray as xr
#         import dask
# 
#         # define topography on the same grid and fill NaNs
#         grid = grid.reindex_like(data, method='nearest').fillna(0)
# 
#         # find stack dim
#         stackvar = data.dims[0] if len(data.dims) == 3 else 'stack'
#         #print ('stackvar', stackvar)
#         shape2d = data.shape[1:] if len(data.dims) == 3 else data.shape
#         #print ('shape2d', shape2d)
# 
#         @dask.delayed
#         def regression_block(stackval, fit_intercept):
#             from sklearn.linear_model import LinearRegression
#             from sklearn.pipeline import make_pipeline
#             from sklearn.preprocessing import StandardScaler
# 
#             # use outer variable
#             data_block = (data.sel({stackvar: stackval}) if stackval is not None else data).compute(n_workers=1)
# 
#             grid_values = grid.values.ravel()
#             data_values = data_block.values.ravel()
#             nanmask = np.isnan(grid_values) | np.isnan(data_values)
#         
#             # build prediction model with or without plane removal (fit_intercept)
#             regr = make_pipeline(StandardScaler(), LinearRegression(fit_intercept=fit_intercept))
#             # fit 1D non-NaNs phase and topography and predict on the non-NaNs 2D topography grid
#             data_grid = regr.fit(np.column_stack([grid_values [~nanmask]]),
#                                  np.column_stack([data_values[~nanmask]]))\
#                         .predict(np.column_stack([grid_values])).reshape(data_block.shape)
#             # cleanup
#             del grid_values, data_values, nanmask, data_block
#             return data_grid
#         
#         stack = []
#         for stackval in data[stackvar].values if len(data.dims) == 3 else [None]:
#             #print ('stackval', stackval)
#             block = dask.array.from_delayed(regression_block(stackval, fit_intercept=fit_intercept),
#                                             shape=shape2d, dtype=np.float32)
#             stack.append(block)
#             del block
# 
#         return xr.DataArray(dask.array.stack(stack) if len(data.dims) == 3 else stack[0],
#                             coords=data.coords)\
#                .rename(data.name)

#     @staticmethod
#     def regression_linear(data, variables, weight=None, valid_pixels_threshold=10000, fit_intercept=True):
#         """
#         topo = sbas.get_topo().coarsen({'x': 4}, boundary='trim').mean()
#         yy, xx = xr.broadcast(topo.y, topo.x)
#         strat_sbas = sbas.regression_linear(unwrap_sbas.phase,
#                 [topo,    topo*yy,    topo*xx,    topo*yy*xx,
#                  topo**2, topo**2*yy, topo**2*xx, topo**2*yy*xx,
#                  topo**3, topo**3*yy, topo**3*xx, topo**3*yy*xx,
#                  yy, xx,
#                  yy**2, xx**2, yy*xx,
#                  yy**3, xx**3, yy**2*xx, xx**2*yy], corr_sbas)
#         """
#         import numpy as np
#         import xarray as xr
#         import dask
#         from sklearn.linear_model import LinearRegression
#         from sklearn.pipeline import make_pipeline
#         from sklearn.preprocessing import StandardScaler
# 
#         if weight is not None and len(weight.dims) == 3 and weight.shape != data.shape:
#             raise Exception(f'Argument "weight" 3D shape {weight.shape} should be equal to "data" 3D shape {data.shape}')
#         if weight is not None and len(weight.dims) == 2 and weight.shape != data.shape[1:]:
#             raise Exception(f'Argument "weight" 2D shape {weight.shape} should be equal to "data" 2D shape {data.shape[1:]}')
# 
#         # find stack dim
#         stackvar = data.dims[0] if len(data.dims) == 3 else 'stack'
#         #print ('stackvar', stackvar)
#         shape2d = data.shape[1:] if len(data.dims) == 3 else data.shape
#         #print ('shape2d', shape2d)
#         chunk2d = data.chunks[1:] if len(data.dims) == 3 else data.chunks
#         #print ('chunk2d', chunk2d)
#     
#         if isinstance(variables, (list, tuple)):
#             variables = xr.concat(variables, dim='stack')
#         elif not isinstance(variables, xr.DataArray) or len(variables.dims) not in (2, 3):
#             raise Exception('Argument "variables" should be 2D or 3D Xarray dataarray of list of 2D Xarray dataarrays')
#         elif len(variables.dims) == 2:
#             variables = variables.expand_dims('stack')
#         elif len(variables.dims) == 3 and not variables.dims[0] == 'stack':
#             raise Exception('Argument "variables" 3D Xarray dataarray needs the first dimension name "stack"')
#         #print ('variables', variables)
# 
#         def regression_block(data, variables, weight, valid_pixels_threshold, fit_intercept):
#             data_values  = data.ravel()
#             variables_values = variables.reshape(-1, variables.shape[-1]).T
#             #assert 0, f'TEST: {data_values.shape}, {variables_values.shape}, {weight.shape}'
#             if weight.size > 1:
#                 weight_values = weight.ravel()
#                 nanmask = np.isnan(data_values) | np.isnan(weight_values) | np.any(np.isnan(variables_values), axis=0)
#             else:
#                 weight_values = None
#                 nanmask = np.isnan(data_values) | np.any(np.isnan(variables_values), axis=0)
# 
#             # regression requires enough amount of valid pixels
#             if data_values.size - np.sum(nanmask) < valid_pixels_threshold:
#                 del data_values, variables_values, weight_values, nanmask
#                 return np.nan * np.zeros(data.shape)
# 
#             # build prediction model with or without plane removal (fit_intercept)
#             regr = make_pipeline(StandardScaler(), LinearRegression(fit_intercept=fit_intercept, copy_X=False, n_jobs=1))
#             fit_params = {'linearregression__sample_weight': weight_values[~nanmask]} if weight.size > 1 else {}
#             regr.fit(variables_values[:, ~nanmask].T, data_values[~nanmask], **fit_params)
#             del weight_values, data_values
#             model = np.full_like(data, np.nan).ravel()
#             model[~nanmask] = regr.predict(variables_values[:, ~nanmask].T)
#             del variables_values, regr
#             return model.reshape(data.shape)
# 
#         # xarray wrapper
#         model = xr.apply_ufunc(
#             regression_block,
#             data,
#             variables.chunk(dict(stack=-1, y=chunk2d[0], x=chunk2d[1])),
#             weight.chunk(dict(y=chunk2d[0], x=chunk2d[1])) if weight is not None else weight,
#             dask='parallelized',
#             vectorize=False,
#             output_dtypes=[np.float32],
#             input_core_dims=[[], ['stack'], []],
#             dask_gufunc_kwargs={'valid_pixels_threshold': valid_pixels_threshold, 'fit_intercept': fit_intercept},
#         )
#         return model

    @staticmethod
    def regression(data, variables, weight=None, algorithm='linear', degree=1, wrap=False, valid_pixels_threshold=1000, **kwargs):
        """
        topo = sbas.get_topo().coarsen({'x': 4}, boundary='trim').mean()
        yy, xx = xr.broadcast(topo.y, topo.x)
        strat_sbas = sbas.regression(unwrap_sbas.phase,
                [topo,    topo*yy,    topo*xx,    topo*yy*xx,
                 topo**2, topo**2*yy, topo**2*xx, topo**2*yy*xx,
                 topo**3, topo**3*yy, topo**3*xx, topo**3*yy*xx,
                 yy, xx,
                 yy**2, xx**2, yy*xx,
                 yy**3, xx**3, yy**2*xx, xx**2*yy], corr_sbas)
    
    
        topo = sbas.interferogram(topophase)
        inc = decimator(sbas.incidence_angle())
        yy, xx = xr.broadcast(topo.y, topo.x)
        variables = [topo,  topo*yy,  topo*xx, topo*yy*xx]
        trend_sbas = sbas.regression(intf_sbas, variables, corr_sbas)
        """
        import numpy as np
        import xarray as xr
        import dask
        from sklearn.linear_model import LinearRegression
        from sklearn.linear_model import SGDRegressor
        from xgboost import XGBRegressor
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import PolynomialFeatures, StandardScaler

        if wrap and algorithm in ('sgd'):
            raise ValueError(f"Unsupported option wrap={wrap} for algorithm {algorithm}.")
        if degree is not None and algorithm in ('xgb'):
            raise ValueError(f"Unsupported option degree={degree} for algorithm {algorithm}.")

        # find stack dim
        stackvar = data.dims[0] if len(data.dims) >= 3 else 'stack'
        #print ('stackvar', stackvar)
        shape2d = data.shape[1:] if len(data.dims) == 3 else data.shape
        #print ('shape2d', shape2d)
        chunk2d = data.chunks[1:] if len(data.dims) == 3 else data.chunks
        #print ('chunk2d', chunk2d)
    
        def regression_block(data, weight, *args, **kwargs):
            data_values  = data.ravel()
            # manage variable number of variables
            variables_stack = np.stack([arg[0] if arg.ndim==3 else arg for arg in args])
            #variables_values = variables_stack.reshape(-1, variables_stack.shape[0]).T
            variables_values = variables_stack.reshape(variables_stack.shape[0], -1)
            del variables_stack
            #assert 0, f'TEST: {data_values.shape}, {variables_values.shape}'
    
            nanmask_data = ~np.isfinite(data_values)
            nanmask_values = np.any(~np.isfinite(variables_values), axis=0)
            if weight.size > 1:
                weight_values = weight.ravel().astype(np.float64)
                nanmask_weight = ~np.isfinite(weight_values)
                nanmask = nanmask_data | nanmask_values | nanmask_weight
                #assert 0, f'TEST weight: {data_values.shape}, {variables_values.shape}, {weight_values.shape}'
            else:
                weight_values = None
                nanmask_weight = None
                nanmask = nanmask_data | nanmask_values
            del nanmask_data, nanmask_weight
    
            # regression requires enough amount of valid pixels
            if data_values.size - np.sum(nanmask) < valid_pixels_threshold:
                del data_values, variables_values, weight_values, nanmask
                return np.nan * np.zeros(data.shape)

            # prepare target Y for regression
            if wrap:
                # convert angles to sine and cosine as (N,2) -> (sin, cos) matrix
                Y = np.column_stack([np.sin(data_values), np.cos(data_values)]).astype(np.float64)
            else:
                # just use data values as (N) matrix
                Y = data_values.reshape(-1).astype(np.float64)
            del data_values

            # build prediction model
            if algorithm == 'linear':
                #regr = make_pipeline(StandardScaler(), LinearRegression(copy_X=False, n_jobs=1, **kwargs))
                regr = make_pipeline(
                    PolynomialFeatures(degree=degree, include_bias=False),
                    StandardScaler(),
                    LinearRegression(copy_X=False, n_jobs=1, **kwargs)
                )
                fit_params = {'linearregression__sample_weight': weight_values[~nanmask]} if weight_values is not None else {}
            elif algorithm == 'sgd':
                #regr = make_pipeline(StandardScaler(), SGDRegressor(**kwargs))
                regr = make_pipeline(
                    PolynomialFeatures(degree=degree, include_bias=False),
                    StandardScaler(),
                    SGDRegressor(**kwargs)
                )
                fit_params = {'sgdregressor__sample_weight': weight_values[~nanmask]} if weight_values is not None else {}
            elif algorithm == 'xgb':
                regr = make_pipeline(StandardScaler(), XGBRegressor(n_jobs=1, **kwargs))
                fit_params = {'xgbregressor__sample_weight': weight_values[~nanmask]} if weight_values is not None else {}
            else:
                raise ValueError(f"Unsupported algorithm {algorithm}. Should be 'linear', 'sgd', or 'xgb'.")
            del weight_values

            regr.fit(variables_values[:, ~nanmask].T, Y[~nanmask], **fit_params)
            del Y, nanmask

            # Predict for all valid pixels
            model_pred = regr.predict(variables_values[:, ~nanmask_values].T)
            del regr, variables_values

            model = np.full_like(data, np.nan).ravel()
            if wrap:
                # (N,2) -> (sin, cos)
                model[~nanmask_values] = np.arctan2(model_pred[:, 0], model_pred[:, 1])
            else:
                # (N,1), just flatten
                model[~nanmask_values] = model_pred.ravel()
            del model_pred, nanmask_values
            
            return model.reshape(data.shape).astype(np.float32)

        dshape = data[0].shape if data.ndim==3 else data.shape
        if isinstance(variables, (list, tuple)):
            vshapes = [v[0].shape if v.ndim==3 else v.shape for v in variables]
            equals = np.all([vshape == dshape for vshape in vshapes])
            if not equals:
                print (f'NOTE: shapes of variables slices {vshapes} and data slice {dshape} differ.')
            #assert equals, f'{dshape} {vshapes}, {equals}'
            variables_stack = [v.reindex_like(data).chunk(dict(y=chunk2d[0], x=chunk2d[1]))  for v in variables]
        else:
            vshape = variables[0].shape if variables.ndim==3 else variables.shape
            if not {vshape} == {dshape}:
                print (f'NOTE: shapes of variables slice {vshape} and data slice {dshape} differ.')
            variables_stack = [variables.reindex_like(data).chunk(dict(y=chunk2d[0], x=chunk2d[1]))]

        if weight is not None:
            if not weight.shape == data.shape:
                print (f'NOTE: shapes of weight {weight.shape} and data {data.shape} differ.')
            weight_stack = weight.reindex_like(data).chunk(dict(y=chunk2d[0], x=chunk2d[1]))
        else:
            weight_stack = None

        # xarray wrapper
        model = xr.apply_ufunc(
            regression_block,
            data,
            weight_stack,
            *variables_stack,
            dask='parallelized',
            vectorize=False,
            output_dtypes=[np.float32],
            dask_gufunc_kwargs={**kwargs},
        )
        del variables_stack

        return model

    def regression_linear(self, data, variables, weight=None, degree=1, wrap=False, valid_pixels_threshold=1000, fit_intercept=True):
        """   
        topo = sbas.get_topo().coarsen({'x': 4}, boundary='trim').mean()
        yy, xx = xr.broadcast(topo.y, topo.x)
        strat_sbas = sbas.regression_linear(unwrap_sbas.phase,
                [topo,    topo*yy,    topo*xx,    topo*yy*xx,
                 topo**2, topo**2*yy, topo**2*xx, topo**2*yy*xx,
                 topo**3, topo**3*yy, topo**3*xx, topo**3*yy*xx,
                 yy, xx,
                 yy**2, xx**2, yy*xx,
                 yy**3, xx**3, yy**2*xx, xx**2*yy], corr_sbas)
        """
        return self.regression(
            data,
            variables,
            weight=weight,
            wrap=wrap,
            valid_pixels_threshold=valid_pixels_threshold,
            algorithm='linear',
            degree=degree,
            fit_intercept=fit_intercept
        )

    def regression_sgd(self, data, variables, weight=None, degree=1, wrap=False, valid_pixels_threshold=1000,
                      penalty='elasticnet', max_iter=1000, tol=1e-3, alpha=0.0001, l1_ratio=0.15):
        """
        Perform regression on a dataset using the SGDRegressor model from scikit-learn.

        This function applies Stochastic Gradient Descent (SGD) regression to fit the given 'data' against a set of 'variables'.
        It's suitable for large datasets and handles high-dimensional features efficiently.

        Parameters:
        data (xarray.DataArray): The target data array to fit.
        variables (xarray.DataArray or list of xarray.DataArray): Predictor variables. It can be a single 3D DataArray or a list of 2D DataArrays.
        weight (xarray.DataArray, optional): Weights for each data point. Useful if certain data points are more important. Defaults to None.
        valid_pixels_threshold (int, optional): Minimum number of valid pixels required for the regression to be performed. Defaults to 10000.
        max_iter (int, optional): Maximum number of passes over the training data (epochs). Defaults to 1000.
        tol (float, optional): Stopping criterion. If not None, iterations will stop when (loss > best_loss - tol) for n_iter_no_change consecutive epochs. Defaults to 1e-3.
        alpha (float, optional): Constant that multiplies the regularization term. Higher values mean stronger regularization. Defaults to 0.0001.
        l1_ratio (float, optional): The Elastic Net mixing parameter, with 0 <= l1_ratio <= 1. l1_ratio=0 corresponds to L2 penalty, l1_ratio=1 to L1. Defaults to 0.15.

        Returns:
        xarray.DataArray: The predicted values as an xarray DataArray, fitted by the SGDRegressor model.

        Notes:
        - SGDRegressor is well-suited for large datasets due to its efficiency in handling large-scale and high-dimensional data.
        - Proper tuning of parameters (max_iter, tol, alpha, l1_ratio) is crucial for optimal performance and prevention of overfitting.

        Example:  
        decimator = sbas.decimator(resolution=15, grid=(1,1))
        topo = decimator(sbas.get_topo())
        inc = decimator(sbas.incidence_angle())
        yy, xx = xr.broadcast(topo.y, topo.x)
        trend_sbas = sbas.regression(unwrap_sbas.phase,
                [topo,    topo*yy,    topo*xx,    topo*yy*xx,
                 topo**2, topo**2*yy, topo**2*xx, topo**2*yy*xx,
                 topo**3, topo**3*yy, topo**3*xx, topo**3*yy*xx,
                 inc,     inc**yy,    inc*xx,     inc*yy*xx,
                 yy, xx,
                 yy**2, xx**2, yy*xx,
                 yy**3, xx**3, yy**2*xx, xx**2*yy], corr_sbas)
        """
        return self.regression(
            data,
            variables,
            weight=weight,
            wrap=wrap,
            valid_pixels_threshold=valid_pixels_threshold,
            algorithm='sgd',
            degree=degree,
            penalty=penalty,
            max_iter=max_iter,
            tol=tol,
            alpha=alpha,
            l1_ratio=l1_ratio
        )

    def regression_xgboost(self, data, variables, weight=None, wrap=False, valid_pixels_threshold=1000,
                           n_estimators=100, learning_rate=0.05, max_depth=6, subsample=0.8, colsample_bytree=1, **kwargs):
        """
        Perform regression on a dataset using XGBoost (XGBRegressor).
        https://xgboost.readthedocs.io/en/stable/python/python_api.html#module-xgboost.sklearn
        https://xgboost.readthedocs.io/en/stable/parameter.html

        Parameters:
        -----------
        data : xarray.DataArray
            The target data array to fit.
        variables : list[xarray.DataArray] or xarray.DataArray
            Predictor variables.
        weight : xarray.DataArray, optional
            Sample weights per data point. Defaults to None.
        valid_pixels_threshold : int, optional
            Minimum valid pixels required for the regression to run. Defaults to 1000.
        n_estimators : int, optional
            Number of boosting rounds. Defaults to 100.
        learning_rate : float, optional
            Step size shrinkage used in update to prevents overfitting. Defaults to 0.05.
        max_depth : int, optional
            Maximum depth of a tree. Defaults to 6.
        kwargs :
            Additional keyword arguments passed to XGBRegressor.

        Returns:
        --------
        xarray.DataArray
            The predicted values as an xarray DataArray, fitted by XGBRegressor.
        """
        return self.regression(
            data,
            variables,
            weight=weight,
            wrap=wrap,
            valid_pixels_threshold=valid_pixels_threshold,
            algorithm='xgb',
            degree=None,
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            max_depth=max_depth,
            subsample=subsample,
            colsample_bytree=colsample_bytree,
            **kwargs
        )

    def polyfit(self, data, weight=None, degree=0, days=None, count=None, wrap=False):
        print ('NOTE: Function is deprecated. Use Stack.regression_pairs() instead.')
        return self.regression_pairs(data=data, weight=weight, degree=degree, days=days, count=count, wrap=wrap)

    def regression_pairs(self, data, weight=None, degree=0, days=None, count=None, wrap=False):
        import xarray as xr
        import pandas as pd
        import numpy as np
        import warnings
        # suppress Dask warning "RuntimeWarning: invalid value encountered in divide"
        warnings.filterwarnings('ignore')
        warnings.filterwarnings('ignore', module='dask')
        warnings.filterwarnings('ignore', module='dask.core')

        multi_index = None
        if 'stack' in data.dims and isinstance(data.coords['stack'].to_index(), pd.MultiIndex):
            multi_index = data['stack']
            data = data.reset_index('stack')
            if weight is not None:
                if not ('stack' in weight.dims and isinstance(weight.coords['stack'].to_index(), pd.MultiIndex)):
                    raise ValueError('ERROR: "weight", if provided, must be stacked consistently with "data".')
                data = data.reset_index('stack')
        else:
            if 'stack' in weight.dims and isinstance(weight.coords['stack'].to_index(), pd.MultiIndex):
                raise ValueError('ERROR: "weight", if provided, must be stacked consistently with "data".')

        pairs, dates = self.get_pairs(data, dates=True)

        models = []
        if wrap:
            models_sin = []
            models_cos = []

        for date in dates:
            data_pairs = pairs[(pairs.ref==date)|(pairs.rep==date)].pair.values
            if weight is None:
                stack = data.sel(pair=data_pairs)
            else:
                stack = data.sel(pair=data_pairs) * np.sqrt(weight.sel(pair=data_pairs))
            del data_pairs

            stack_days = xr.where(stack.ref < pd.Timestamp(date),
                           (stack.ref - stack.rep).dt.days,
                           (stack.rep - stack.ref).dt.days)
            # select smallest intervals
            stack_days_selected = stack_days[np.argsort(np.abs(stack_days.values))][:count]
            if days is not None:
                stack_days_selected = stack_days_selected[np.abs(stack_days_selected)<=days]

            selected_pairs = (np.sign(stack_days)*stack).assign_coords(time=stack_days)\
                [stack.pair.isin(stack_days_selected.pair)]\
                .swap_dims({'pair': 'time'})\
                .sortby(['ref', 'rep'])
            del stack, stack_days, stack_days_selected

            if not wrap:
                linear_fit = selected_pairs.polyfit(dim='time', deg=degree)
                model = linear_fit.polyfit_coefficients.sel(degree=degree).astype(np.float32)
                models.append(model.assign_coords(date=pd.to_datetime(date)))
                del model, linear_fit
            else:
                # fit sine and cosine components
                linear_fit_sin = np.sin(selected_pairs).polyfit(dim='time', deg=degree)
                linear_fit_cos = np.cos(selected_pairs).polyfit(dim='time', deg=degree)

                model_sin = linear_fit_sin.polyfit_coefficients.sel(degree=degree).astype(np.float32)
                model_cos = linear_fit_cos.polyfit_coefficients.sel(degree=degree).astype(np.float32)

                models_sin.append(model_sin.assign_coords(date=pd.to_datetime(date)))
                models_cos.append(model_cos.assign_coords(date=pd.to_datetime(date)))
                del model_sin, model_cos, linear_fit_sin, linear_fit_cos

            del selected_pairs

        if not wrap:
            model = xr.concat(models, dim='date')
            del models
            out = xr.concat(
                [
                    (model.sel(date=ref).drop('date') - model.sel(date=rep).drop('date'))
                    .assign_coords(pair=str(ref.date()) + ' ' + str(rep.date()), ref=ref, rep=rep)
                    for ref, rep in zip(pairs['ref'], pairs['rep'])
                ],
                dim='pair'
            ).rename(data.name)
        else:
            # combine separate sin and cos models
            model_sin = xr.concat(models_sin, dim='date')
            model_cos = xr.concat(models_cos, dim='date')
            del models_sin, models_cos

            angle_diffs = []
            for ref, rep in zip(pairs['ref'], pairs['rep']):
                sin_ref = model_sin.sel(date=ref).drop('date')
                cos_ref = model_cos.sel(date=ref).drop('date')
                sin_rep = model_sin.sel(date=rep).drop('date')
                cos_rep = model_cos.sel(date=rep).drop('date')

                # compute angle differences using sin/cos difference formula
                # sin(A−B) = sin A * cos B − cos A * sin B
                sin_diff = sin_ref * cos_rep - cos_ref * sin_rep
                # cos(A−B) = cos A * cos B+ sin A * sin B
                cos_diff = cos_ref * cos_rep + sin_ref * sin_rep
                del sin_ref, cos_ref, sin_rep, cos_rep

                angle_diff = np.arctan2(sin_diff, cos_diff)\
                             .assign_coords(pair=str(ref.date()) + ' ' + str(rep.date()), ref=ref, rep=rep)
                angle_diffs.append(angle_diff)
                del angle_diff, sin_diff, cos_diff

            out = xr.concat(angle_diffs, dim='pair').rename(data.name)
            del angle_diffs

        if multi_index is not None:
            return out.assign_coords(stack=multi_index)
        return out

#     def polyfit(self, data, weight=None, degree=0, variable=None, count=None):
#         import xarray as xr
#         import pandas as pd
#         import numpy as np
# 
#         pairs, dates = self.get_pairs(data, dates=True)
#         if variable is not None:
#             pairs['variable'] = variable.values if isinstance(variable, pd.Series) else variable
# 
#         models = []
#         for date in dates:
#             data_pairs = pairs[(pairs.ref==date)|(pairs.rep==date)].pair.values
#             #print (data_pairs)
#             stack = data.sel(pair=data_pairs)
#             if weight is None:
#                 stack = data.sel(pair=data_pairs)
#             else:
#                 stack = data.sel(pair=data_pairs) * np.sqrt(weight.sel(pair=data_pairs))
#             # days, positive and negative
#             days = xr.where(stack.ref < pd.Timestamp(date),
#                            (stack.ref - stack.rep).dt.days,
#                            (stack.rep - stack.ref).dt.days)
#             # select smallest intervals
#             days_selected = days[np.argsort(np.abs(days.values))][:count]
#             if variable is not None:
#                 data_variables = xr.DataArray(pairs[pairs.pair.isin(data_pairs)]['variable'].values, coords=days.coords)
#             else:
#                 data_variables = days
#             #print (days, days_selected, data_variables)
#             #.sortby(['ref', 'rep'])
#             linear_fit = (np.sign(days)*stack)\
#                 .assign_coords(time=data_variables)[stack.pair.isin(days_selected.pair)]\
#                 .swap_dims({'pair': 'variable'})\
#                 .polyfit(dim='variable', deg=degree)
#             model = linear_fit.polyfit_coefficients.sel(degree=degree)
#             models.append(model.assign_coords(date=pd.to_datetime(date)))
#             del data_pairs, stack, days, days_selected, data_variables, linear_fit, model
#         model = xr.concat(models, dim='date')
#         del models
# 
#         out = xr.concat([(model.sel(date=ref).drop('date') - model.sel(date=rep).drop('date'))\
#                                  .assign_coords(pair=str(ref.date()) + ' ' + str(rep.date()), ref=ref, rep=rep) \
#                           for ref, rep in zip(pairs['ref'], pairs['rep'])], dim='pair')
# 
#         return out.rename(data.name)

    def gaussian(self, data, wavelength, truncate=3.0, resolution=60, debug=False):
        """
        Apply a lazy Gaussian filter to an input 2D or 3D data array.

        Parameters
        ----------
        data : xarray.DataArray
            The input data array with NaN values allowed.
        wavelength : float
            The cut-off wavelength for the Gaussian filter in meters.
        truncate : float, optional
            Size of the Gaussian kernel, defined in terms of standard deviation, or 'sigma'. 
            It is the number of sigmas at which the window (filter) is truncated. 
            For example, if truncate = 3.0, the window will cut off at 3 sigma. Default is 3.0.
        resolution : float, optional
            The processing resolution for the Gaussian filter in meters.
        debug : bool, optional
            Whether to print debug information.

        Returns
        -------
        xarray.DataArray
            The filtered data array with the same coordinates as the input.

        Examples
        --------
        Detrend ionospheric effects and solid Earth's tides on a large area and save to disk:
        stack.stack_gaussian2d(slcs, wavelength=400)
        For band-pass filtering apply the function twice and save to disk:
        model = stack.stack_gaussian2d(slcs, wavelength=400, interactive=True) \
            - stack.stack_gaussian2d(slcs, wavelength=2000, interactive=True)
        stack.save_cube(model, caption='Gaussian Band-Pass filtering')

        Detrend and return lazy xarray dataarray:
        stack.stack_gaussian2d(slcs, wavelength=400, interactive=True)
        For band-pass filtering apply the function twice:
        stack.stack_gaussian2d(slcs, wavelength=400, interactive=True) \
            - stack.stack_gaussian2d(slcs, wavelength=2000, interactive=True) 

        """
        import xarray as xr
        import numpy as np
#         import warnings
#         # suppress Dask warning "RuntimeWarning: invalid value encountered in divide"
#         warnings.filterwarnings('ignore')
#         warnings.filterwarnings('ignore', module='dask')
#         warnings.filterwarnings('ignore', module='dask.core')

        assert self.is_ra(data), 'ERROR: the processing requires grid in radar coordinates'
        assert np.issubdtype(data.dtype, np.floating), 'ERROR: expected float datatype input data'
        assert wavelength is not None, 'ERROR: Gaussian filter cut-off wavelength is not defined'

        # ground pixel size
        dy, dx = self.get_spacing(data)
        # downscaling
        yscale, xscale = int(np.round(resolution/dy)), int(np.round(resolution/dx))
        # gaussian kernel
        #sigma_y = np.round(wavelength / dy / yscale, 1)
        #sigma_x = np.round(wavelength / dx / xscale, 1)
        if debug:
            print (f'DEBUG: gaussian: ground pixel size in meters: y={dy:.1f}, x={dx:.1f}')
        if (xscale <=1 and yscale <=1) or (wavelength/resolution <= 3):
            # decimation is useless
            return self.multilooking(data, wavelength=wavelength, coarsen=None, debug=debug)

        # define filter on decimated grid, the correction value is typically small
        wavelength_dec = np.sqrt(wavelength**2 - resolution**2)
        if debug:
            print (f'DEBUG: gaussian: downscaling to resolution {resolution}m using yscale {yscale}, xscale {xscale}')
            #print (f'DEBUG: gaussian: filtering on {resolution}m grid using sigma_y0 {sigma_y}, sigma_x0 {sigma_x}')
            print (f'DEBUG: gaussian: filtering on {resolution}m grid using wavelength {wavelength_dec:.1f}')

        # find stack dim
        stackvar = data.dims[0] if len(data.dims) == 3 else 'stack'
        #print ('stackvar', stackvar)

        # split coordinate grid to equal chunks and rest
        ys_blocks = np.array_split(data.y, np.arange(0, data.y.size, self.chunksize)[1:])
        xs_blocks = np.array_split(data.x, np.arange(0, data.x.size, self.chunksize)[1:])

        data_dec = self.multilooking(data, wavelength=resolution, coarsen=(yscale,xscale), debug=debug)
        data_dec_gauss = self.multilooking(data_dec, wavelength=wavelength_dec, debug=debug)
        del data_dec
    
        stack = []
        for stackval in data[stackvar].values if len(data.dims) == 3 else [None]:
            data_in = data_dec_gauss.sel({stackvar: stackval}) if stackval is not None else data_dec_gauss
            data_out = data_in.reindex({'y': data.y, 'x': data.x}, method='nearest').chunk(self.chunksize)
            del data_in
            stack.append(data_out)
            del data_out

        # wrap lazy Dask array to Xarray dataarray
        if len(data.dims) == 2:
            out = stack[0]
        else:
            out = xr.concat(stack, dim=stackvar)
        del stack

        # append source data coordinates excluding removed y, x ones
        for (k,v) in data.coords.items():
            if k not in ['y','x']:
                out[k] = v

        return out

#     def detrend(self, dataarray, fit_intercept=True, fit_dem=True, fit_coords=True,
#                 resolution=90, debug=False):
#         """
#         Detrend and return output for a single unwrapped interferogram combining optional topography and linear components removal.
# 
#         Parameters
#         ----------
#         dataarray : xarray.DataArray
#             The input data array to detrend.
#         fit_intercept : bool, optional
#             Whether to remove the mean value (plane) from the data. Default is True.
#         fit_dem : bool, optional
#             Whether to detrend the topography. Default is True.
#         fit_coords : bool, optional
#             Whether to detrend the linear coordinate components. Default is True.
#         resolution : int, optional
#             The processing resolution to prevent overfitting and reduce grid size. Default is 90.
#         debug : bool, optional
#             Whether to print debug information. Default is False.
# 
#         Returns
#         -------
#         xarray.DataArray
#             The detrended 2D data array.
# 
#         Examples
#         --------
#         Simplest detrending:
#         unwrap_detrended = stack.detrend(pair.values[0] if isinstance(pairs, pd.DataFrame) else pair[0])
# 
#         Detrend unwrapped interferogram in radar coordinates, see for details:
#         - [GitHub Issue 98](https://github.com/gmtsar/gmtsar/issues/98)
#         - [GitHub Issue 411](https://github.com/gmtsar/gmtsar/issues/411)
#         """
#         import xarray as xr
#         import numpy as np
#         import dask
#         from sklearn.linear_model import LinearRegression
#         from sklearn.pipeline import make_pipeline
#         from sklearn.preprocessing import StandardScaler
# 
#         def postprocessing(out):
#             return out.astype(np.float32).rename('detrend')
# 
#         # check the simplest case
#         if not fit_intercept and not fit_dem and not fit_coords:
#             print ('NOTE: All the detrending options disable, function does nothing')
#             return dataarray
# 
#         # check simple case
#         if fit_intercept and not fit_dem and not fit_coords:
#             if debug:
#                 print ('DEBUG: Remove mean value only')
#             return postprocessing(dataarray - dataarray.mean())
# 
#         # input grid can be too large
#         decimator = self.pixel_decimator(resolution=resolution, grid=dataarray, debug=debug)
#         # decimate
#         dataarray_dec = decimator(dataarray)
#         if debug:
#             print ('DEBUG: Decimated data array', dataarray_dec.shape)
# 
#         # topography grid required to fit_dem option only
#         if fit_dem:
#             if debug:
#                 print ('DEBUG: Interpolate topography on the data grid')
#             topo = self.get_topo()
#             #topo = topo.reindex_like(unwraps[0], method='nearest')
#             # use xr.zeros_like to prevent the target grid coordinates modifying
#             topo = topo.reindex_like(dataarray, method='nearest')
#             # check chunks
#             if debug:
#                 print ('DEBUG: regrid to resolution in meters', resolution)
#             # decimate
#             topo_dec  = decimator(topo)
#             if debug:
#                 print ('DEBUG: Decimated topography array', topo_dec.shape)
#         else:
#             topo = topo_dec = None
# 
#         # lazy calculations are useless below
#         def data2fit(data, elev, yy, xx):
#             y = data.values.reshape(-1) if isinstance(data, xr.DataArray) else data.reshape(-1)
#             nanmask = np.isnan(y)
#             # prepare regression variable
#             Y = y[~nanmask]
# 
#             if fit_coords or fit_dem:
#                 # prepare coordinates for X regression variable
#                 ys = (yy.values.reshape(-1) if isinstance(yy, xr.DataArray) else yy.reshape(-1))[~nanmask]
#                 xs = (xx.values.reshape(-1) if isinstance(xx, xr.DataArray) else xx.reshape(-1))[~nanmask]
# 
#             if fit_dem:
#                 # prepare topography for X regression variable
#                 zs = (elev.values.reshape(-1) if isinstance(elev, xr.DataArray) else elev.reshape(-1))[~nanmask]
#                 zys = zs*ys
#                 zxs = zs*xs
# 
#             if fit_dem and fit_coords:
#                 X = np.column_stack([zys, zxs, ys, xs, zs])
#             elif fit_dem:
#                 X = np.column_stack([zys, zxs, zs])
#             elif fit_coords:
#                 X = np.column_stack([ys, xs])
#             return Y, X, nanmask
# 
#         if debug:
#             print ('DEBUG: linear regression calculation')
# 
#         def regr_fit():
#             # build prediction model with or without plane removal (fit_intercept)
#             regr = make_pipeline(StandardScaler(), LinearRegression(fit_intercept=fit_intercept))
#             yy, xx = xr.broadcast(dataarray_dec.y, dataarray_dec.x)
#             Y, X, _ = data2fit(dataarray_dec, topo_dec, yy, xx)
# 
#             return regr.fit(X, Y)
# 
#         # calculate for chunks
#         def predict(data, elev, yy, xx, regr):
#             Y, X, nanmask = data2fit(data, elev, yy, xx)
#             # the chunk is NaN-filled, prediction impossible
#             if nanmask.all():
#                 return data
#             # predict when some values are not NaNs
#             model = np.nan * np.zeros(data.shape)
#             model.reshape(-1)[~nanmask] = regr.predict(X)
#             # return data without the trend
#             return data - model
# 
#         def regr_predict(regr):
#             yy = xr.DataArray(dataarray.y).chunk(-1)
#             xx = xr.DataArray(dataarray.x).chunk(-1)
#             yy, xx = xr.broadcast(yy, xx)
# 
#             # xarray wrapper
#             return xr.apply_ufunc(
#                 predict,
#                 dataarray,
#                 topo.chunk(dataarray.chunks) if topo is not None else None,
#                 yy.chunk(dataarray.chunks),
#                 xx.chunk(dataarray.chunks),
#                 dask='parallelized',
#                 vectorize=False,
#                 output_dtypes=[np.float32],
#                 dask_gufunc_kwargs={'regr': regr},
#             )
# 
#         # build the model and return the input data without the detected trend
#         return postprocessing(regr_predict(regr_fit()))

#     def gaussian(self, grid, wavelength, truncate=3.0, resolution=90, debug=False):
#         """
#         Apply a lazy Gaussian filter to an input 2D or 3D data array.
# 
#         Parameters
#         ----------
#         dataarray : xarray.DataArray
#             The input data array with NaN values allowed.
#         wavelength : float
#             The cut-off wavelength for the Gaussian filter in meters.
#         truncate : float, optional
#             Size of the Gaussian kernel, defined in terms of standard deviation, or 'sigma'. 
#             It is the number of sigmas at which the window (filter) is truncated. 
#             For example, if truncate = 3.0, the window will cut off at 3 sigma. Default is 3.0.
#         resolution : float, optional
#             The processing resolution for the Gaussian filter in meters.
#         debug : bool, optional
#             Whether to print debug information.
# 
#         Returns
#         -------
#         xarray.DataArray
#             The filtered data array with the same coordinates as the input.
# 
#         Examples
#         --------
#         Detrend ionospheric effects and solid Earth's tides on a large area and save to disk:
#         stack.stack_gaussian2d(slcs, wavelength=400)
#         For band-pass filtering apply the function twice and save to disk:
#         model = stack.stack_gaussian2d(slcs, wavelength=400, interactive=True) \
#             - stack.stack_gaussian2d(slcs, wavelength=2000, interactive=True)
#         stack.save_cube(model, caption='Gaussian Band-Pass filtering')
# 
#         Detrend and return lazy xarray dataarray:
#         stack.stack_gaussian2d(slcs, wavelength=400, interactive=True)
#         For band-pass filtering apply the function twice:
#         stack.stack_gaussian2d(slcs, wavelength=400, interactive=True) \
#             - stack.stack_gaussian2d(slcs, wavelength=2000, interactive=True) 
# 
#         """
#         import xarray as xr
#         import numpy as np
# 
#         assert self.is_ra(grid), 'ERROR: the processing requires grid in radar coordinates'
#         assert wavelength is not None, 'ERROR: Gaussian filter cut-off wavelength is not defined'
# 
#         # ground pixel size
#         dy, dx = self.get_spacing(grid)
#         # reduction
#         yscale, xscale = int(np.round(resolution/dy)), int(np.round(resolution/dx))
#         # gaussian kernel
#         sigma_y = np.round(wavelength / dy / yscale)
#         sigma_x = np.round(wavelength / dx / xscale)
#         if debug:
#             print (f'DEBUG: average ground pixel size in meters: y={dy}, x={dx}')
#             print (f'DEBUG: yscale {yscale}, xscale {xscale} to resolution {resolution} m')
#             print ('DEBUG: Gaussian filtering using resolution, sigma_y, sigma_x', resolution, sigma_y, sigma_x)
# 
#         # find stack dim
#         stackvar = grid.dims[0] if len(grid.dims) == 3 else 'stack'
#         #print ('stackvar', stackvar)
#     
#         stack = []
#         for stackval in grid[stackvar].values if len(grid.dims) == 3 else [None]:
#             block = grid.sel({stackvar: stackval}) if stackval is not None else grid
#             block_dec = self.antialiasing_downscale(block, wavelength=resolution, coarsen=(yscale,xscale), debug=debug)
#             gaussian_dec = self.nanconvolve2d_gaussian(block_dec, (sigma_y,sigma_x), truncate=truncate)
#             # interpolate decimated filtered grid to original resolution
#             gaussian = gaussian_dec.interp_like(block, method='nearest')
#             # revert the original chunks
#             gaussian = xr.unify_chunks(block, gaussian)[1]
#             stack.append(gaussian.astype(np.float32).rename('gaussian'))
# 
#         # wrap lazy Dask array to Xarray dataarray
#         if len(grid.dims) == 2:
#             out = stack[0]
#         else:
#             out = xr.concat(stack, dim=stackvar)
#         del stack
# 
#         # append source grid coordinates excluding removed y, x ones
#         for (k,v) in grid.coords.items():
#             if k not in ['y','x']:
#                 out[k] = v
#     
#         return out

#     def turbulence(self, phase, date_crop=0, symmetrical=False):
#         pairs, dates = self.get_pairs(phase, dates=True)
#     
#         turbos = []
#         for date in dates:
#             ref = pairs[pairs.ref==date]
#             rep = pairs[pairs.rep==date]
#             # calculate left and right pairs
#             if symmetrical:
#                 count = min(len(ref), len(rep))
#             else:
#                 count = None
#             #print (date, len(ref), len(rep), '=>', count)
#             if len(ref) < 1 or len(rep) < 1:
#                 # correction calculation is not possible
#                 #turbo = xr.zeros_like((detrend - phase_topo).isel(pair=0)).drop(['pair','ref','rep'])
#                 continue
#             else:
#                 ref_data = phase.sel(pair=ref.pair.values).isel(pair=slice(None,count))
#                 #ref_weight = 1/corr60m.sel(pair=ref_data.pair)
#                 #print (ref_data)
#                 rep_data = phase.sel(pair=rep.pair.values ).isel(pair=slice(None,count))
#                 #rep_weight = 1/corr60m.sel(pair=rep_data.pair)
#                 #print (rep_data)
#                 #mask = (ref_weight.sum('pair') + rep_weight.sum('pair'))/2/count
#                 turbo = (ref_data.mean('pair') - rep_data.mean('pair')) / 2
#                 #turbo = ((ref_data*ref_weight).mean('pair')/ref_weight.sum('pair') -\
#                 #         (rep_data*rep_weight).mean('pair')/rep_weight.sum('pair')) / 2
#                 #.where(mask>MASK)
#             turbos.append(turbo.assign_coords(date=pd.to_datetime(date)))
#             del turbo
#         turbo = xr.concat(turbos, dim='date')
#         del turbos
#     
#         # convert dates to pairs
#         #pairs = pairs[pairs.ref.isin(turbo.date.values)&pairs.rep.isin(turbo.date.values)]
#         fake = xr.zeros_like(phase.isel(pair=0))
# 
#     #     return [(
#     #         (turbo.sel(date=ref).drop('date') if ref in turbo.date else fake) - \
#     #         (turbo.sel(date=rep).drop('date') if rep in turbo.date else fake)
#     #     ).assign_coords(pair=str(ref.date()) + ' ' + str(rep.date()), ref=ref, rep=rep) \
#     #     for ref, rep in zip(pairs['ref'], pairs['rep'])]
#     
#     
#         dates_crop = dates[date_crop:None if date_crop is None or date_crop==0 else -date_crop]
#         pairs_crop = pairs[pairs.ref.isin(dates_crop)&pairs.rep.isin(dates_crop)]
#     
#     #     refs = [ref for ref in pairs['ref'] if str(ref.date()) in dates]
#     #     reps = [rep for rep in pairs['rep'] if str(rep.date()) in dates]
#     
#         phase_turbo = xr.concat([(
#             (turbo.sel(date=ref).drop('date') if ref in turbo.date else fake) - \
#             (turbo.sel(date=rep).drop('date') if rep in turbo.date else fake)
#         ).assign_coords(pair=str(ref.date()) + ' ' + str(rep.date()), ref=ref, rep=rep) \
#         for ref, rep in zip(pairs_crop['ref'], pairs_crop['rep'])], dim='pair')
#     
#     #     phase_turbo = xr.concat([(turbo.sel(date=ref) - turbo.sel(date=rep))\
#     #                              .assign_coords(pair=str(ref.date()) + ' ' + str(rep.date()), ref=ref, rep=rep) \
#     #                              for ref, rep in \
#     #                              zip(pairs['ref'], pairs['rep'])],
#     #                        dim='pair')
#         #phase_turbo['ref'].values = pd.to_datetime(phase_turbo['ref'])
#         #phase_turbo['rep'].values = pd.to_datetime(phase_turbo['rep'])
#         return phase_turbo

#     def turbulence(self, phase, weight=None, date_crop=1, symmetrical=False):
#         import xarray as xr
#         import pandas as pd
# 
#         pairs, dates = self.get_pairs(phase, dates=True)
# 
#         turbos = []
#         for date in dates:
#             ref = pairs[pairs.ref==date]
#             rep = pairs[pairs.rep==date]
#             # calculate left and right pairs
#             count = min(len(ref), len(rep)) if symmetrical else None
#             #print (date, len(ref), len(rep), '=>', count)
#             if len(ref) < 1 or len(rep) < 1:
#                 # correction calculation is not possible
#                 continue
#             ref_data = phase.sel(pair=ref.pair.values).isel(pair=slice(None,count))
#             #print (ref_data)
#             rep_data = phase.sel(pair=rep.pair.values ).isel(pair=slice(None,count))
#             #print (rep_data)
#             if weight is not None:
#                 ref_weight = weight.sel(pair=ref_data.pair)
#                 rep_weight = weight.sel(pair=rep_data.pair)
#                 turbo = ((ref_data*ref_weight).mean('pair')/ref_weight.sum('pair') -\
#                          (rep_data*rep_weight).mean('pair')/rep_weight.sum('pair')) / 2
#                 del ref_weight, rep_weight
#             else:
#                 turbo = (ref_data.mean('pair') - rep_data.mean('pair')) / 2
#             del ref_data, rep_data
#             turbos.append(turbo.assign_coords(date=pd.to_datetime(date)))
#             del turbo
#         turbo = xr.concat(turbos, dim='date')
#         del turbos
# 
#         # empty grid
#         empty = xr.zeros_like(phase.isel(pair=0))
#         # convert dates to pairs
#         dates_crop = dates[date_crop:None if date_crop is None or date_crop==0 else -date_crop]
#         pairs_crop = pairs[pairs.ref.isin(dates_crop) & pairs.rep.isin(dates_crop)]  
#         phase_turbo = xr.concat([(
#             (turbo.sel(date=ref).drop('date') if ref in turbo.date else empty) - \
#             (turbo.sel(date=rep).drop('date') if rep in turbo.date else empty)
#         ).assign_coords(pair=str(ref.date()) + ' ' + str(rep.date()), ref=ref, rep=rep) \
#         for ref, rep in zip(pairs_crop['ref'], pairs_crop['rep'])], dim='pair')
#         del empty, dates_crop, pairs_crop
# 
#         return phase_turbo.rename('turbulence')

    def turbulence(self, phase, weight=None):
        import xarray as xr
        import pandas as pd

        print ('NOTE: this function is deprecated, use instead Stack.polyfit()')

        pairs, dates = self.get_pairs(phase, dates=True)

        turbos = []
        for date in dates:
            ref = pairs[pairs.ref==date]
            rep = pairs[pairs.rep==date]
            #print (date, len(ref), len(rep))
            ref_data = phase.sel(pair=ref.pair.values)
            #print (ref_data)
            rep_data = phase.sel(pair=rep.pair.values)
            #print (rep_data)
            if weight is not None:
                ref_weight = weight.sel(pair=ref.pair.values)
                rep_weight = weight.sel(pair=rep.pair.values)
                turbo = xr.concat([ref_data*ref_weight, -rep_data*rep_weight], dim='pair').sum('pair')/\
                    xr.concat([ref_weight, rep_weight], dim='pair').sum('pair')
                del ref_weight, rep_weight
            else:
                turbo = xr.concat([ref_data, -rep_data], dim='pair').mean('pair')
            del ref_data, rep_data
            turbos.append(turbo.assign_coords(date=pd.to_datetime(date)))
            del turbo
        turbo = xr.concat(turbos, dim='date')
        del turbos

        phase_turbo = xr.concat([(turbo.sel(date=ref).drop('date') - turbo.sel(date=rep).drop('date'))\
                                 .assign_coords(pair=str(ref.date()) + ' ' + str(rep.date()), ref=ref, rep=rep) \
                          for ref, rep in zip(pairs['ref'], pairs['rep'])], dim='pair')

        return phase_turbo.rename('turbulence')

    def velocity(self, data):
        import pandas as pd
        import numpy as np
        #years = ((data.date.max() - data.date.min()).dt.days/365.25).item()
        #nanoseconds = (data.date.max().astype(int) - data.date.min().astype(int)).item()
        #print ('years', np.round(years, 3), 'nanoseconds', nanoseconds)
        multi_index = None
        if 'stack' in data.dims and isinstance(data.coords['stack'].to_index(), pd.MultiIndex):
            multi_index = data.coords['stack']
            # replace multiindex by sequential numbers 0,1,...
            data = data.reset_index('stack')
        #velocity = nanoseconds*data.polyfit('date', 1).polyfit_coefficients.sel(degree=1)/years
        nanoseconds_per_year = 365.25*24*60*60*1e9
        # calculate slope per year
        velocity = nanoseconds_per_year*data.polyfit('date', 1).polyfit_coefficients.sel(degree=1).astype(np.float32).rename('trend')
        if multi_index is not None:
            return velocity.assign_coords(stack=multi_index)
        return velocity

#     def trend(self, data, deg=1):
#         import xarray as xr
#         if 'date' in data.dims:
#             return xr.polyval(data.date, data.polyfit('date', deg).polyfit_coefficients).rename('trend')
#         elif 'pair' in data.dims:
#             return xr.polyval(data.pair, data.polyfit('pair', deg).polyfit_coefficients).rename('trend')
#         raise ValueError("The 'data' argument must include a 'date' or 'pair' dimension to detect trends.")
#     

    def plot_velocity(self, data, caption='Velocity, [rad/year]',
                      quantile=None, vmin=None, vmax=None, symmetrical=False, aspect=None, alpha=1, **kwargs):
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
        data.plot.imshow(vmin=vmin, vmax=vmax, alpha=alpha, cmap='turbo')
        self.plot_AOI(**kwargs)
        self.plot_POI(**kwargs)
        if aspect is not None:
            plt.gca().set_aspect(aspect)
        if self.is_ra(data):
            plt.xlabel('Range')
            plt.ylabel('Azimuth')
        plt.title(caption)

    def plot_velocity_los_mm(self, data, caption='Velocity, [mm/year]',
                      quantile=None, vmin=None, vmax=None, symmetrical=False, aspect=None, alpha=1, **kwargs):
        self.plot_velocity(self.los_displacement_mm(data),
                           caption=caption, aspect=aspect, alpha=alpha,
                           quantile=quantile, vmin=vmin, vmax=vmax, symmetrical=symmetrical, **kwargs)

    def trend(self, data, dim='auto', degree=1):
        print ('NOTE: Function is deprecated. Use Stack.regression1d() instead.')
        return self.regression1d(data=data, dim=dim, degree=degree)

    def regression1d(self, data, dim='auto', degree=1, wrap=False):
        import xarray as xr
        import pandas as pd
        import numpy as np

        multi_index = None
        if 'stack' in data.dims and isinstance(data.coords['stack'].to_index(), pd.MultiIndex):
            multi_index = data['stack']
            # detect unused coordinates
            unused_coords = [d for d in multi_index.coords if not d in multi_index.dims and not d in multi_index.indexes]
            # cleanup multiindex to merge it with the processed dataset later
            multi_index = multi_index.drop_vars(unused_coords)
            data = data.reset_index('stack')

        stackdim = [_dim for _dim in ['date', 'pair'] if _dim in data.dims]
        if len(stackdim) != 1:
            raise ValueError("The 'data' argument must include a 'date' or 'pair' dimension to detect trends.")
        stackdim = stackdim[0]
    
        if isinstance(dim, str) and dim == 'auto':
            dim = stackdim

        # add new coordinate using 'dim' values
        if not isinstance(dim, str):
            if isinstance(dim, (xr.DataArray, pd.DataFrame, pd.Series)):
                dim_da = xr.DataArray(dim.values, dims=[stackdim])
            else:
                dim_da = xr.DataArray(dim, dims=[stackdim])
            data_dim = data.assign_coords(polyfit_coord=dim_da).swap_dims({'pair': 'polyfit_coord'})
            
        if wrap:
            # wrap to prevent outrange
            data = self.wrap(data)
            # fit sine/cosine
            trend_sin = self.regression1d(np.sin(data), dim, degree=degree, wrap=False)
            trend_cos = self.regression1d(np.cos(data), dim, degree=degree, wrap=False)
            # define the angle offset at zero baseline
            trend_sin0 = xr.polyval(xr.DataArray(0, dims=[]), trend_sin.coefficients)
            trend_cos0 = xr.polyval(xr.DataArray(0, dims=[]), trend_cos.coefficients)
            fit = np.arctan2(trend_sin, trend_cos) - np.arctan2(trend_sin0, trend_cos0)
            del trend_sin, trend_cos, trend_sin0, trend_cos0
            # wrap to prevent outrange
            return self.wrap(fit)

        # add new coordinate using 'dim' values
        if not isinstance(dim, str):
            # fit the specified values
            # Polynomial coefficients, highest power first, see numpy.polyfit
            fit_coeff = data_dim.polyfit('polyfit_coord', degree).polyfit_coefficients.astype(np.float32)
            fit = xr.polyval(data_dim['polyfit_coord'], fit_coeff)\
                .swap_dims({'polyfit_coord': stackdim}).drop_vars('polyfit_coord').astype(np.float32).rename('trend')
            out = xr.merge([fit, fit_coeff]).rename(polyfit_coefficients='coefficients')
            if multi_index is not None:
                return out.assign_coords(stack=multi_index)
            return out
    
        # fit existing coordinate values
        # Polynomial coefficients, highest power first, see numpy.polyfit
        fit_coeff = data.polyfit(dim, degree).polyfit_coefficients.astype(np.float32)
        fit = xr.polyval(data[dim], fit_coeff).astype(np.float32).rename('trend')
        out = xr.merge([fit, fit_coeff]).rename(polyfit_coefficients='coefficients')
        if multi_index is not None:
            return out.assign_coords(stack=multi_index)
        return out
