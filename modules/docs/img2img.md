Run stable diffusion with an initial image. This requires a prompt as in `txt2img`, but also requires either an uploaded image or an image url as the initial image. Your image will most likely be rescaled, pay attention to the rescale mode you choose. (and if you are using `autosize`, which is `True` by default)

* autosize tries to automatically set your width and height such that the dimensions are both within autosize_maxsize, while keeping the aspect ratio intact.   * scale, if provided, will apply scale to the provided `width` and `height`, not the image dimensions. This overrides autosize, if set.
* A response of "unknown error" usually means OOM. If it repeats for a given set of parameters, reduce image size, adjust upscaler, or batch size. Note that latent upscaling is the most memory efficient.