import time


class WorkItem:
    def __init__(self, model: str, vae: str, prompt: str, neg_prompt: str, width: int, height: int, steps: int, cfg: float, sampler: str, seed: int, batch_size: int, message_id: int):
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
        self.message_id = message_id
        self.creation_time = time.time()

        self.scale = 1
        self.images = []
        self.error_message = "unknown error"
        self.upscaler = None
        self.highres_steps = None
        self.denoising_str = None

    def set_highres(self, scale: float, upscaler: str, highres_steps: int, denoising_str: float):
        self.scale = scale
        self.upscaler = upscaler
        self.highres_steps = highres_steps
        self.denoising_str = denoising_str
