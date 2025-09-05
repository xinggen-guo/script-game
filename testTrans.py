import torch
import torch.nn as nn
import torch.nn.functional as F

# 假设：我们输入的是 3 个词，每个词是 4 维向量
# 输入形状：[batch_size=1, seq_len=3, embedding_dim=4]
x = torch.tensor([[[1.0, 0.0, 1.0, 0.0],
                   [0.0, 1.0, 0.0, 1.0],
                   [1.0, 1.0, 1.0, 1.0]]])  # shape: (1, 3, 4)

class MiniTransformer(nn.Module):
    def __init__(self, dim=4):
        super().__init__()
        self.q = nn.Linear(dim, dim, bias=False)
        self.k = nn.Linear(dim, dim, bias=False)
        self.v = nn.Linear(dim, dim, bias=False)
        self.ff = nn.Sequential(
            nn.Linear(dim, dim * 2),
            nn.ReLU(),
            nn.Linear(dim * 2, dim)
        )
        self.norm1 = nn.LayerNorm(dim)
        self.norm2 = nn.LayerNorm(dim)

    def forward(self, x):
        # Attention
        q = self.q(x)
        k = self.k(x)
        v = self.v(x)
        attn_scores = torch.matmul(q, k.transpose(-2, -1)) / (x.size(-1) ** 0.5)  # (B, seq, seq)
        attn_weights = F.softmax(attn_scores, dim=-1)
        attn_output = torch.matmul(attn_weights, v)

        # 残差连接 + LayerNorm
        x = self.norm1(x + attn_output)

        # Feedforward
        ff_output = self.ff(x)
        x = self.norm2(x + ff_output)
        return x

# 初始化并运行
model = MiniTransformer(dim=4)
output = model(x)
print("输出向量：", output)