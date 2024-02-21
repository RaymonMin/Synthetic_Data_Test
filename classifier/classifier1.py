import os
import torch
import torch.nn as nn
import torch.optim as optim
import os
import random
import time

from setting import opt
from torchvision import transforms, models
from torchvision.datasets import ImageFolder
from torch.utils.data import DataLoader, Dataset
from PIL import Image
from tqdm import tqdm

def main():
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")



    def calculate_accuracy(model, data_loader):
        model.eval()  
        correct = 0
        total = 0
        with torch.no_grad(): 
            for inputs, labels in data_loader:
                inputs = inputs.to(device)
                labels = labels.to(device)
                outputs = model(inputs)
                _, predicted = torch.max(outputs.data, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
        accuracy = 100 * correct / total
        return accuracy

    def predict_image(image_path, model, transform):
        model.eval()
        image = Image.open(image_path).convert('RGB')
        image = transform(image)
        image = image.unsqueeze(0).to(device)  # 确保图像也在正确的设备上
        with torch.no_grad():
            outputs = model(image)
        _, predicted = torch.max(outputs, 1)
        return predicted.item()


    class CustomDataset(Dataset):
        def __init__(self, gen_root_dir, train_set_root_dir, transform=None, epochs_index=0, split='train', split_ratio=opt.split_ratio):
            self.transform = transform
            self.samples = []
            self.split = split
            self.split_ratio = split_ratio
            self._load_dataset(gen_root_dir, train_set_root_dir, epochs_index)

        def _load_dataset(self, gen_root_dir, train_set_root_dir, epochs_index):
                        
            if self.split == 'train' and epochs_index in range(0,1000):
                for label in os.listdir(gen_root_dir):
                    label_dir = os.path.join(gen_root_dir, label)
                    epoch_dir = os.path.join(label_dir, f'epoch{epochs_index}')
                    if os.path.exists(epoch_dir):
                        for img_name in os.listdir(epoch_dir):
                            self.samples.append((os.path.join(epoch_dir, img_name), int(label.replace('label', ''))))
            elif self.split == 'test' and  epochs_index in range(0,1000):
                print("No generated images for test set.")
            elif epochs_index == 'false':
                print("No generated images used.")
            else:
                print("Invalid epochs_index type.")

            temp_samples = []
            for label in os.listdir(train_set_root_dir):
                train_label_dir = os.path.join(train_set_root_dir, label)
                label_samples = [(os.path.join(train_label_dir, img_name), int(label.replace('label', ''))) for img_name in os.listdir(train_label_dir)]
                random.shuffle(label_samples)
                split_point = int(len(label_samples) * self.split_ratio)
                if self.split == 'train':
                    temp_samples.extend(label_samples[:split_point])
                else:  
                    temp_samples.extend(label_samples[split_point:])

            self.samples.extend(temp_samples)

            print(f"Loaded {len(self.samples)} samples.")

        def __len__(self):
            return len(self.samples)

        def __getitem__(self, idx):
            img_path, label = self.samples[idx]
            image = Image.open(img_path).convert('RGB')
            if self.transform:
                image = self.transform(image)
            return image, label

    transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    train_dataset = CustomDataset(gen_root_dir=opt.gen_dir,
                                train_set_root_dir=opt.train_dir,
                                transform=transform,
                                epochs_index=opt.epochs_index,
                                split='train',
                                split_ratio=opt.split_ratio)

    test_dataset = CustomDataset(gen_root_dir=opt.gen_dir,
                                train_set_root_dir=opt.train_dir,
                                transform=transform,
                                epochs_index=opt.epochs_index,
                                split='test',
                                split_ratio=opt.split_ratio)

    train_loader = DataLoader(train_dataset, batch_size=opt.batch_size, shuffle=True)

    num_classes = opt.num_classes
    resnet = models.resnet50(weights='imagenet')
    resnet.fc = nn.Linear(resnet.fc.in_features, num_classes)
    resnet = resnet.to(device)  # 这行已经足够，之后的相同代码应该删除


    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(resnet.parameters(), lr=0.001, momentum=0.9)

    for epoch in range(opt.epochs):
        print(f"Epoch {epoch + 1}/{opt.epochs} begins.")
        start_time = time.time()
        
        progress_bar = tqdm(train_loader, desc=f"Epoch {epoch + 1}/{opt.epochs}", leave=True, ncols=100)
        for inputs, labels in progress_bar:
            inputs = inputs.to(device)
            labels = labels.to(device)
            optimizer.zero_grad()
            outputs = resnet(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            progress_bar.set_postfix(loss=f"{loss.item():.4f}")

        print("accuracy: ", calculate_accuracy(resnet, train_loader))
        if not os.path.exists('Acc.'):
            os.makedirs('Acc.')

        with open(os.path.join('Acc.', f'accuracy_epoch{opt.epochs_index}.txt'), 'w') as f:
            f.write(f'Traing Acc. for epoch{epoch+1} is {accuracy:.2f}%')


        train_time = time.time() - start_time
        print(f"Epoch {epoch + 1}/{opt.epochs} ends. Loss: {loss.item():.4f}. Time: {train_time:.2f}s.")
        
        progress_bar.close()

    test_loader = DataLoader(test_dataset, batch_size=opt.batch_size, shuffle=False)

    accuracy = calculate_accuracy(resnet, test_loader)
    print(f'Test Accuracy: {accuracy:.2f}%')

    if not os.path.exists('Acc.'):
        os.makedirs('Acc.')

    with open(os.path.join('Acc.', f'accuracy_epoch{opt.epochs_index}.txt'), 'w') as f:
        f.write(f'Test Acc. is {accuracy:.2f}%')


if __name__ == "__main__":
    main()

