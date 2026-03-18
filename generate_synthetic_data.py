import os
import torch
import csv
import random
from torchvision.utils import save_image

def generate_tabular_data(output_dir = "edge_data/tabular" , num_samples = 500):
    """Generates a CSV file with 10 random numerical features and a target label."""
    os.makedirs(output_dir , exist_ok=True)
    file_path = os.path.join(output_dir , "local_records.csv")

    with open(file_path , mode='w' , newline="") as file:
        writer = csv.writer(file)
        # Write the header
        header = [f"feature_{i}" for i in range(10)] + ["target"]
        writer.writerow(header)

        # Write the random data
        for _ in range(num_samples):
            # Generate 10 random floats between 0 and 1
            features = [round(random.uniform(0 , 1) , 4) for _ in range(10)]
            # Generate a random binary target (0 or 1)
            target = random.choice([0 , 1])
            writer.writerow(features + [target])

    print(f"Generated {num_samples} tabular records at {file_path}")

def generate_image_data(output_dir = "edge_data/images" , num_samples_per_class = 100):
    """Generates synthetic 28x28 grayscale images split into 2 classes."""
    classes = ["class_0" , "class_1"]

    for cls in classes:
        cls_dir = os.path.join(output_dir , cls)
        os.makedirs(cls_dir , exist_ok=True)

        for i in range(num_samples_per_class):
            # Create a fake 1-channel, 28x28 image tensor
            img_tensor = torch.randn(1 , 28 , 28)
            file_path = os.path.join(cls_dir , f"img_{i}.png")
            # Save it physically to the hard drive
            save_image(img_tensor , file_path)
    
    total = len(classes) * num_samples_per_class
    print(f"Generated {total} image files at {output_dir}")

if __name__ == '__main__':
    print("--- Starting Synthectic Data Generation ---")
    generate_tabular_data()
    generate_image_data()
    print("--- Generation Complete ---")