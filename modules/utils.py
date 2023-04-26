import inspect
from functools import wraps


def async_add_arguments(arguments: dict):
    def decorator(func):
        sig = inspect.signature(func)
        parameters = list(sig.parameters.values())

        # remove kwargs from function signature
        parameters.pop()

        # the expected number of args when we invoke func
        func_param_len = len(parameters)

        # create new param list, based off arguments dict
        for arg_name, arg_data in arguments.items():
            parameters.append(
                inspect.Parameter(
                    arg_name,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=arg_data["type"]
                )
            )

        new_sig = sig.replace(parameters=parameters)

        # new func takes in anything, lmao
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # since func takes in only its args + kwargs dict, fix up args here
            # we expect args to have additional params
            func_args = []
            for i, arg in enumerate(args):
                if i < func_param_len:
                    func_args.append(arg)
                else:
                    kwargs[parameters[i].name] = arg

            await func(*func_args, **kwargs)
        wrapper.__signature__ = new_sig
        return wrapper
    return decorator


def max_batch_size(width: int, height: int, scale: float, upscaler: str) -> int:
    if scale > 1:
        if upscaler == 'Latent':
            if width * height > 512 * 1024:
                if scale > 1.5:
                    return 0
                return 1
            elif width * height > 512 * 512:
                return 2
            return 4
        else:
            if scale > 1:
                if width * height > 512 * 1024:
                    return 0
                elif width * height > 512 * 512:
                    return 1
                return 2
    return 4
