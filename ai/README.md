# AI training setup

Goal: train a LoRA for "black Chevrolet Gentra 2024 Sport tuning" using ~50-100 real photos.

- Copy your raw photos into `datasets/raw/sport_gentra/`.
- `prepare_sport_gentra_dataset.py` will center-crop and resize images to 768x768, then write a default caption per image into `processed/sport_gentra/captions.txt` alongside resized files in `processed/sport_gentra/images/`.
- `training/colab_sport_gentra_lora.md` will outline Google Colab steps with diffusers + PyTorch to train the LoRA.

