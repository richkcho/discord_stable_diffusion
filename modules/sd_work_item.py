"""
This module contains the WorkItem class, which represents an item of work to be processed by stable diffusion.
"""

import time


class SDWorkItem:
    """
    The SDWorkItem class represents an item of work to be processed by stable diffusion.

    Attributes:
        - model (str): the name of the model to use for image generation.
        - vae (str): the name of the VAE to use for image generation.
        - prompt (str): the text prompt to use for image generation.
        - neg_prompt (str): the negative text prompt to use for image generation.
        - width (int): the width of the generated image.
        - height (int): the height of the generated image.
        - steps (int): the number of steps to run the generation process for.
        - cfg (float): the config parameter to use for the generation process.
        - sampler (str): the sampler to use for image generation.
        - seed (int): the seed to use for the generation process.
        - batch_size (int): the batch size to use for the generation process.
        - context_handle (str): the context handle to use for the generation process.
        - creation_time (float): the time at which the WorkItem was created.
        - scale (float): the scale of the high-resolution image.
        - images (list): a list of generated images.
        - error_message (str): an error message to display if an error occurs during the generation process.
        - upscaler (str): the upscaler to use for the high-resolution image generation.
        - highres_steps (int): the number of steps to run the high-resolution image generation process for.
        - denoising_str (float): the denoising strength to use for the high-resolution image generation process.

    Methods:
        - set_highres(self, scale: float, upscaler: str, highres_steps: int, denoising_str: float): sets the attributes related to high-resolution image generation.
    """

    def __init__(self, model: str, vae: str, prompt: str, neg_prompt: str, width: int, height: int, steps: int, cfg: float, sampler: str, seed: int, batch_size: int, context_handle: str, refiner: str, refiner_switch_at: float):
        """
        Class representing a work item for stable diffusion image generation.

        Args:
            model (str): The name of the stable diffusion model.
            vae (str): The name of the VAE model.
            prompt (str): The text prompt for generating the image.
            neg_prompt (str): The negative text prompt for generating the image.
            width (int): The width of the image.
            height (int): The height of the image.
            steps (int): The number of steps to run for generating the image.
            cfg (float): The value of classifier free guidance to use for generating the image.
            sampler (str): The sampler method to use for generating the image.
            seed (int): The seed value to use for generating the image.
            batch_size (int): The batch size for generating the image.
            context_handle (str): The context handle for generating the image.
        """
        self.model = model
        self.vae = vae
        self.prompt = prompt
        self.neg_prompt = neg_prompt
        self.width = width
        self.height = height
        self.steps = steps
        self.cfg = cfg
        self.sampler = sampler
        self.seed = seed
        self.batch_size = batch_size
        self.context_handle = context_handle
        self.refiner = refiner
        self.refiner_switch_at = refiner_switch_at
        self.creation_time = time.time()

        self.error_message = "unknown error"

        self.scale = 1
        self.upscaler = None
        self.highres_steps = None
        self.denoising_str = None

        self.image_b64 = None
        self.resize_mode = 0

        self.images = []

    def set_highres(self, scale: float, upscaler: str, highres_steps: int, denoising_str: float):
        """
        Set the high-resolution image generation parameters.

        Args:
            scale (float): The scaling factor to use for generating the high-resolution image.
            upscaler (str): The upscaler method to use for generating the high-resolution image.
            highres_steps (int): The number of steps to run for generating the high-resolution image.
            denoising_str (float): The denoising strength to use for generating the high-resolution image.
        """
        self.scale = scale
        self.upscaler = upscaler
        self.highres_steps = highres_steps
        self.denoising_str = denoising_str

    def set_image(self, image_b64: str, denoising_str: float, resize_mode: int):
        """
        Set the parameters for img2img

        Args:
            image_b64 (str): the base64 encoded image
            denoising_str (float): The denoising strength to use.
            resize_mode (int): The resize mode to use(see consts).
        """
        self. image_b64 = image_b64
        self.denoising_str = denoising_str
        self.resize_mode = resize_mode
