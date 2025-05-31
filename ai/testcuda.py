import torch
print(torch.__version__)
print(torch.version.cuda)
print(torch.cuda.is_available())  # 應該要顯示 True
print(torch.cuda.device_count())  # 顯示可用 GPU 數量
print(torch.cuda.current_device())  # 顯示目前預設 GPU id
print(torch.cuda.get_device_name(0))  # 顯示第一張卡的名稱（如果有 GPU）
