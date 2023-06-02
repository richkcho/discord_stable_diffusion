# Discord UI for stable-diffusion-webui

## Commands
Supported slash commands:
* /set_preferences
    * sets per-user default values of some parameters used for image generation. Check `consts.py` for a list and 
    description of possible values
* /get_preferences
    * retrieves a list of all set preferences
* /info
    * gets information about the supported models, vaes, embeddings, and loras supported. Also usage of the other commands. 
* /txt2img
    * Given a prompt, make image(s). 
* /img2img
    * Given a prompt and image, make image(s).
* /again
    * Given a previous message (either message id or message content), do more (de)generating. 


You can read more detailed documentation in the `modules/docs` folder. You should be able to find it [here](https://github.com/richkcho/discord_stable_diffusion/blob/master/modules/docs/). 

## Multi-GPU support
For higher throughput, this ui supports multiple GPUs or multiple systems, provided they are accessible over the network. It assumes you have at least 8 GB VRAM on each card, and you're 
using a card that supports `xformers`. 