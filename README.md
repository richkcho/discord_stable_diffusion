# Discord UI for stable-diffusion-webui

## Commands
See `modules/consts.py` for a list of commands. Some keywords are "special" in that they are not associated 
with any configuration. Most commands are to set configuration for a single prompt query, or to set your personal 
default for a configuration parameter. 

The format of a discord message is of newline separated `<keyword>: <string>` pairs. For example,
```
prompt: <some prompt here>
neg-prompt: <the negative prompt>
<config>: <value>
```

## Multi-GPU support
For higher throughput, this ui supports multiple GPUs on a single computer. In theory this can be extended for 
multi-computer multi-gpu setups, but thats a TODO. It assumes you have at least 8 GB VRAM on each card, and you're 
using a card that supports `xformers`. 