"""
Some utility functions for the discord stable diffusion modules. 

Functions:
- async_add_arguments: Decorator to "modify" the signature of a function according to the input dictionary
- max_batch_size: Computes the maximum image batch size that can be handled by the supported GPUs
"""
import inspect
from functools import wraps


def async_add_arguments(arguments: dict):
    """
    A decorator function to modify the signature of a function based on the input dictionary.

    Args:
    arguments (dict): A dictionary of arguments to be added to the function signature. Each key in the dictionary is 
    an argument name, and the corresponding value is another dictionary with the following keys:
        - type (type): The type of the argument.

    Returns:
    A function that has its signature modified according to the input dictionary.
    """
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
    """
    Computes the maximum image batch size that can be handled by the supported GPUs.

    Args:
    width (int): The width of the input image.
    height (int): The height of the input image.
    scale (float): The upscale factor of the image
    upscaler (str): The upscaler to be used, if the image is upscaled.

    Returns:
    The maximum batch size of images that can be processed.
    """
    if scale > 1:
        if upscaler == 'Latent':
            if width * height > 512 * 1024:
                if scale > 1.5:
                    return 0
                return 1

            if width * height > 512 * 512:
                return 2
            return 4

        # R-ESRGAN upscalers use more memory
        if scale > 1:
            if width * height > 512 * 1024:
                return 0
            if width * height > 512 * 512:
                return 1
            return 2
    return 4
