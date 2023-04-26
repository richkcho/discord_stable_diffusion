# Discord UI for stable-diffusion-webui

## Commands
Supported slash commands:
* /set_preferences
* /get_preferences
* /info
* /generate
* /again

Each of these commands come with a small description, please read those. 

## Multi-GPU support
For higher throughput, this ui supports multiple GPUs on a single computer. In theory this can be extended for 
multi-computer multi-gpu setups, but thats a TODO. It assumes you have at least 8 GB VRAM on each card, and you're 
using a card that supports `xformers`. 