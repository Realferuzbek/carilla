# Colab spec: Sport Gentra LoRA training (diffusers)

## Overview
- Stack: PyTorch + diffusers (with transformers, accelerate, safetensors).
- Base model: photoreal Stable Diffusion v1.5–style checkpoint from Hugging Face.
- Training: LoRA fine-tuning on ~50–100 Sport Gentra images at 768x768.

## Notebook structure (cells)
1) **Install deps**: pip install torch, diffusers, transformers, accelerate, safetensors (CUDA build of torch if Colab GPU supports it).  
2) **Mount Drive**: mount Google Drive; set a working directory inside Drive for datasets/checkpoints/outputs.  
3) **Set paths**: define `DATA_DIR` pointing to the folder containing `images/` and `captions.txt` (from `processed/sport_gentra`). Define output/checkpoint dirs.  
4) **Load base model**: download/load the SD 1.5 photoreal model; enable attention slicing/xformers if available; prepare it for LoRA training.  
5) **Dataset class**: implement a custom Dataset that pairs each image file with its caption line; apply basic augmentations if desired (e.g., horizontal flip).  
6) **Hyperparameters**: set batch size, learning rate, gradient accumulation, number of steps or epochs, seed, max grad norm, and optimizer/scheduler choices.  
7) **LoRA setup**: wrap attention modules with LoRA adapters; ensure only LoRA parameters are trainable (freeze base weights).  
8) **Training loop**: run training steps updating only LoRA params; log loss periodically; respect mixed precision if available.  
9) **Checkpointing**: save periodic LoRA checkpoints and a final `sport_gentra_lora.safetensors` into Drive.  
10) **Test cell (img2img)**: run an img2img pass on a sample Gentra photo using the trained LoRA; visualize outputs inline in Colab.  
11) **Cleanup/notes**: remind to unmount Drive if needed.

## After training
- Download the final `sport_gentra_lora.safetensors` file from Drive.  
- Later, load these weights in a separate Python FastAPI service for inference. The FastAPI app will inject the LoRA into a compatible base model for generation or img2img.  
- Keep the dataset backed up; you may want to rerun with tweaked hyperparameters (lr, steps, batch size) to refine quality.  
