import torch.nn as nn
import torch.nn.functional as F

class SimpleCNN(nn.Module):
    """A basic Convolutional Neural Network for Image Data"""
    def __init__(self):
        super(SimpleCNN , self).__init__()
        self.conv1 = nn.Conv2d(1 , 32 , kernel_size=3 , stride=1 , padding=1)
        self.conv2 = nn.Conv2d(32 , 64 , kernel_size=3 , stride=1 , padding=1)
        self.fc1 = nn.Linear(64 * 7 * 7 , 128)
        self.fc2 = nn.Linear(128 , 10)
    
    def forward(self , x):
        x = F.relu(F.max_pool2d(self.conv1(x) , 2))
        x = F.relu(F.max_pool2d(self.conv2(x) , 2))
        x = x.view(-1 , 64 * 7 * 7)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x
    
class SimpleMLP(nn.Module):
    """A basic Multi-Layer Perceptron for Numerical Data"""
    def __init__(self, input_size = 10 , hidden_size = 64 , num_classses = 2):
        super(SimpleMLP , self).__init__()
        self.fc1 = nn.Linear(input_size , hidden_size)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size , hidden_size)
        self.fc3 = nn.Linear(hidden_size , num_classses)
    
    def forward(self , x):
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        x = self.fc3(x)
        return x
    