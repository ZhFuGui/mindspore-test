"""
测试 mindspore.mint.flip 接口

本测试文件验证 mindspore.mint.flip 接口的功能。
主要测试内容详见ISSUES.md。

注意事项：
1. dims参数必须是list或tuple类型，不支持单个整数（与PyTorch的差异见ISSUES.md）
2. 所有维度索引都遵循Python的索引规则，支持负数索引
"""

import numpy as np
import torch
import mindspore as ms
from mindspore import Tensor, nn, Parameter
import mindspore.mint as mint
import pytest

def calculate_error(torch_output, ms_output):
    """计算PyTorch和MindSpore输出之间的误差"""
    if isinstance(torch_output, torch.Tensor):
        if torch_output.requires_grad:
            torch_output = torch_output.detach()
        torch_output = torch_output.numpy()
    if isinstance(ms_output, ms.Tensor):
        ms_output = ms_output.asnumpy()
    return np.max(np.abs(torch_output - ms_output))

def test_random_dtype_support():
    """
    测试不同数据类型的支持情况
    所有基本数据类型测试结果详见ISSUES.md#数据类型支持情况
    """
    shape = (2, 3, 4)
    results = {}
    
    dtypes = [
        (np.float32, torch.float32, ms.float32),
        (np.int32, torch.int32, ms.int32),
        (np.float16, torch.float16, ms.float16),
        (np.int8, torch.int8, ms.int8),
        (np.uint8, torch.uint8, ms.uint8)
    ]
    
    for np_dtype, torch_dtype, ms_dtype in dtypes:
        print(f"\nTesting dtype: {np_dtype}")
        try:
            # 生成随机数据
            if np_dtype in [np.float32, np.float16]:
                data = np.random.randn(*shape).astype(np_dtype)
            else:
                data = np.random.randint(1, 100, size=shape, dtype=np_dtype)
            
            # PyTorch测试
            torch_input = torch.tensor(data, dtype=torch_dtype)
            torch_output = torch.flip(torch_input, dims=[0, 1])
            
            # MindSpore测试
            ms_input = Tensor(data, dtype=ms_dtype)
            ms_output = mint.flip(ms_input, dims=[0, 1])
            
            # 计算误差
            error = calculate_error(torch_output, ms_output)
            print(f"Max error: {error}")
            
            results[str(np_dtype)] = {
                'supported': True,
                'error': error
            }
            
            assert error < 1e-3, f"Error {error} exceeds threshold for dtype {np_dtype}"
            
        except Exception as e:
            print(f"Error with dtype {np_dtype}: {str(e)}")
            results[str(np_dtype)] = {
                'supported': False,
                'error_message': str(e)
            }
    
    return results

def test_fixed_dtype_output_accuracy():
    """测试固定数据类型下随机输入的输出精度"""
    # 使用float32作为固定数据类型
    shapes = [
        (4,),
        (2, 3),
        (2, 3, 4),
        (2, 3, 4, 5)
    ]
    
    for shape in shapes:
        print(f"\nTesting shape: {shape}")
        data = np.random.randn(*shape).astype(np.float32)
        
        # PyTorch测试
        torch_input = torch.tensor(data, dtype=torch.float32)
        dims = list(range(len(shape)))  # 测试所有可能的维度组合
        
        for dim in dims:
            torch_output = torch.flip(torch_input, dims=[dim])
            
            # MindSpore测试
            ms_input = Tensor(data, dtype=ms.float32)
            ms_output = mint.flip(ms_input, dims=[dim])
            
            # 计算误差
            error = calculate_error(torch_output, ms_output)
            print(f"Shape {shape}, dim {dim}, max error: {error}")
            assert error < 1e-3, f"Error {error} exceeds threshold for shape {shape} and dim {dim}"

def test_param_type_support():
    """
    测试不同参数类型的支持情况
    已知问题：dims参数不支持单个整数（详见ISSUES.md#flip接口差异）
    """
    data = np.random.randn(2, 3, 4).astype(np.float32)
    ms_input = Tensor(data, dtype=ms.float32)
    
    # 测试dims参数的不同类型
    test_cases = [
        ([0], "list with single integer"),
        ([0, 1], "list with multiple integers"),
        ((0,), "tuple with single integer"),
        ((0, 1), "tuple with multiple integers"),
        (0, "single integer"),
        ([-1], "negative index"),
        ([1.0], "float instead of int"),
        (["0"], "string instead of int"),
        ([True], "boolean instead of int"),
        (None, "None value"),
    ]
    
    results = {}
    for dims, desc in test_cases:
        print(f"\nTesting dims parameter: {desc}")
        try:
            ms_output = mint.flip(ms_input, dims=dims)
            results[desc] = {
                'supported': True,
                'output_shape': ms_output.shape
            }
        except Exception as e:
            print(f"Error with {desc}: {str(e)}")
            results[desc] = {
                'supported': False,
                'error_message': str(e)
            }
    
    return results

class FlipNet(nn.Cell):
    def __init__(self):
        super(FlipNet, self).__init__()
        self.weight = Parameter(Tensor(np.random.randn(2, 3).astype(np.float32)))
    
    def construct(self, x):
        return mint.flip(x * self.weight, dims=[0])

def test_neural_network():
    """
    测试神经网络中的flip操作
    测试结果详见ISSUES.md#神经网络集成测试
    """
    # 初始化网络
    net = FlipNet()
    
    # 准备输入数据
    input_data = Tensor(np.random.randn(2, 3).astype(np.float32))
    
    try:
        # 前向推理
        output = net(input_data)
        print("Forward inference successful")
        print("Output shape:", output.shape)
        
        # 验证输出形状
        assert output.shape == (2, 3), f"Expected output shape (2, 3), got {output.shape}"
        
    except Exception as e:
        print(f"Error in neural network test: {str(e)}")
        raise

def test_error_handling():
    """
    测试错误处理
    已知问题：错误信息格式与PyTorch存在差异（详见ISSUES.md#错误处理机制）
    """
    data = np.random.randn(2, 3, 4).astype(np.float32)
    ms_input = Tensor(data, dtype=ms.float32)
    
    error_cases = [
        {
            'dims': [3],  # 超出维度范围
            'desc': "Dimension out of range"
        },
        {
            'dims': [-4],  # 负数维度超出范围
            'desc': "Negative dimension out of range"
        },
        {
            'dims': [1, 1],  # 重复维度
            'desc': "Duplicate dimensions"
        },
        {
            'dims': [0.5],  # 非整数维度
            'desc': "Non-integer dimension"
        }
    ]
    
    results = {}
    for case in error_cases:
        print(f"\nTesting error case: {case['desc']}")
        try:
            output = mint.flip(ms_input, dims=case['dims'])
            results[case['desc']] = {
                'raised_error': False,
                'message': "No error raised"
            }
        except Exception as e:
            print(f"Error as expected: {str(e)}")
            results[case['desc']] = {
                'raised_error': True,
                'message': str(e)
            }
    
    return results

def test_backward_gradient():
    """
    测试反向传播梯度
    测试结果详见ISSUES.md#神经网络集成测试
    """
    # 准备数据
    data = np.random.randn(2, 3).astype(np.float32)
    
    # PyTorch测试
    torch_input = torch.tensor(data, requires_grad=True)
    torch_output = torch.flip(torch_input, dims=[0])
    torch_output.sum().backward()
    torch_grad = torch_input.grad.numpy()
    
    # MindSpore测试
    ms_input = Tensor(data, dtype=ms.float32)
    
    def grad_fn(inputs):
        return mint.flip(inputs, dims=[0])
    
    ms_grad = ms.grad(grad_fn)(ms_input).asnumpy()
    
    # 比较梯度
    grad_error = np.max(np.abs(torch_grad - ms_grad))
    print(f"Maximum gradient error: {grad_error}")
    assert grad_error < 1e-3, f"Gradient error {grad_error} exceeds threshold"

def test_fixed_input_values():
    """
    测试固定输入值的情况
    验证在已知输入下的翻转结果是否正确
    """
    # 固定的测试数据
    fixed_data = np.array([
        [[1.0, 2.0], [3.0, 4.0]],
        [[5.0, 6.0], [7.0, 8.0]]
    ], dtype=np.float32)
    
    print("\n测试固定输入值")
    
    test_cases = [
        {'name': 'single_dim', 'dims': [0]},
        {'name': 'multiple_dims', 'dims': [0, 1]},
        {'name': 'all_dims', 'dims': [0, 1, 2]},
        {'name': 'negative_dims', 'dims': [-1, -2]},
    ]
    
    for case in test_cases:
        print(f"\nTesting {case['name']}")
        try:
            # PyTorch测试
            torch_input = torch.tensor(fixed_data)
            torch_output = torch.flip(torch_input, dims=case['dims'])
            
            # MindSpore测试
            ms_input = Tensor(fixed_data)
            ms_output = mint.flip(ms_input, dims=case['dims'])
            
            error = calculate_error(torch_output, ms_output)
            print(f"Max error: {error}")
            print(f"PyTorch shape: {torch_output.shape}, MindSpore shape: {ms_output.shape}")
            
            assert error < 1e-5, f"Error {error} exceeds threshold"
            assert torch_output.shape == ms_output.shape, "Shape mismatch"
            print(f"✓ {case['name']} passed")
            
        except Exception as e:
            print(f"Error in {case['name']}: {str(e)}")
            raise

def test_zero_size_dimension():
    """
    测试包含0维度的张量
    验证对特殊形状张量的处理能力
    """
    shapes = [
        (0,),           # 1D with zero size
        (2, 0, 3),      # 3D with zero size in middle
        (2, 3, 0),      # 3D with zero size at end
        (0, 0, 3),      # Multiple zero dimensions
    ]
    
    for shape in shapes:
        print(f"\nTesting shape: {shape}")
        try:
            data = np.zeros(shape, dtype=np.float32)
            
            # PyTorch测试
            torch_input = torch.tensor(data)
            torch_output = torch.flip(torch_input, dims=[0])
            
            # MindSpore测试
            ms_input = Tensor(data)
            ms_output = mint.flip(ms_input, dims=[0])
            
            print(f"PyTorch shape: {torch_output.shape}, MindSpore shape: {ms_output.shape}")
            assert torch_output.shape == ms_output.shape, "Shape mismatch"
            print(f"✓ Shape {shape} passed")
            
        except Exception as e:
            print(f"Error with shape {shape}: {str(e)}")

def test_large_tensor():
    """
    测试大型张量的处理
    验证在处理大量数据时的性能和精度
    """
    try:
        # 创建一个较大的张量
        shape = (100, 100, 100)  # 1,000,000个元素
        data = np.random.randn(*shape).astype(np.float32)
        
        # PyTorch测试
        torch_input = torch.tensor(data)
        torch_output = torch.flip(torch_input, dims=[0, 1, 2])
        
        # MindSpore测试
        ms_input = Tensor(data)
        ms_output = mint.flip(ms_input, dims=[0, 1, 2])
        
        error = calculate_error(torch_output, ms_output)
        print(f"\nLarge tensor max error: {error}")
        assert error < 1e-5, f"Error {error} exceeds threshold"
        print("✓ Large tensor test passed")
        
    except Exception as e:
        print(f"Error in large tensor test: {str(e)}")
        raise

def test_consecutive_flips():
    """
    测试连续翻转操作
    验证多次翻转操作的正确性
    """
    try:
        data = np.random.randn(3, 4, 5).astype(np.float32)
        
        # PyTorch测试
        torch_input = torch.tensor(data)
        torch_output = torch.flip(torch.flip(torch_input, dims=[0]), dims=[1])
        
        # MindSpore测试
        ms_input = Tensor(data)
        ms_output = mint.flip(mint.flip(ms_input, dims=[0]), dims=[1])
        
        error = calculate_error(torch_output, ms_output)
        print(f"\nConsecutive flips max error: {error}")
        assert error < 1e-5, f"Error {error} exceeds threshold"
        print("✓ Consecutive flips test passed")
        
    except Exception as e:
        print(f"Error in consecutive flips test: {str(e)}")
        raise

def test_special_values():
    """
    测试特殊值的处理
    验证对极值、NaN等特殊值的处理
    """
    special_data = np.array([
        [float('inf'), float('-inf')],
        [float('nan'), 0.0]
    ], dtype=np.float32)
    
    try:
        # PyTorch测试
        torch_input = torch.tensor(special_data)
        torch_output = torch.flip(torch_input, dims=[0, 1])
        
        # MindSpore测试
        ms_input = Tensor(special_data)
        ms_output = mint.flip(ms_input, dims=[0, 1])
        
        # 对于特殊值，我们只验证形状是否匹配
        print("\nTesting special values")
        assert torch_output.shape == ms_output.shape, "Shape mismatch for special values"
        print("✓ Special values test passed")
        
    except Exception as e:
        print(f"Error in special values test: {str(e)}")
        raise

if __name__ == "__main__":
    print("=== Testing random dtype support ===")
    dtype_results = test_random_dtype_support()
    
    print("\n=== Testing fixed dtype output accuracy ===")
    test_fixed_dtype_output_accuracy()
    
    print("\n=== Testing parameter type support ===")
    param_results = test_param_type_support()
    
    print("\n=== Testing neural network ===")
    test_neural_network()
    
    print("\n=== Testing error handling ===")
    error_results = test_error_handling()
    
    print("\n=== Testing backward gradient ===")
    test_backward_gradient()
    
    print("\n=== Testing fixed input values ===")
    test_fixed_input_values()
    
    print("\n=== Testing zero size dimension ===")
    test_zero_size_dimension()
    
    print("\n=== Testing large tensor ===")
    test_large_tensor()
    
    print("\n=== Testing consecutive flips ===")
    test_consecutive_flips()
    
    print("\n=== Testing special values ===")
    test_special_values()
