Used to re-run commands with alterations. Requires either the message id of the "`Generating n images...`" acknowledgement message or resulting image post, or the contents of the first acknowledgement message.

* If an image is supplied, will assume you are trying to run an `img2img` command. 
* A response of "unknown error" usually means OOM. If it repeats for a given set of parameters, reduce image size, adjust upscaler, or batch size. Note that latent upscaling is the most memory efficient.