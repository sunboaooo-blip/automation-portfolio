"""Product cutout with local BiRefNet (no upload). usage: cutout.py IN.png OUT.png"""
import os
import sys
import torch
from PIL import Image
from torchvision import transforms
from transformers import AutoModelForImageSegmentation

M = os.environ.get("BIREFNET", "ZhengPeng7/BiRefNet")
model = AutoModelForImageSegmentation.from_pretrained(M, trust_remote_code=True).eval().to("cuda").half()
img = Image.open(sys.argv[1]).convert("RGB")
t = transforms.Compose([transforms.Resize((1024, 1024)), transforms.ToTensor(),
                        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
with torch.no_grad():
    pred = model(t(img).unsqueeze(0).to("cuda").half())[-1].sigmoid().cpu()[0].squeeze().float()
mask = transforms.ToPILImage()(pred).resize(img.size)
img.putalpha(mask)
img.crop(img.getbbox()).save(sys.argv[2])
print("cutout", img.getbbox())
