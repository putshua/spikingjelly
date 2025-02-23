try:
    import cupy
    import torch
    import time
    import numpy as np
    from .. import configure
    import os
    import threading
    import datetime

    def cal_fun_t(n, device, f, *args, **kwargs):
        if n <= 2:
            torch.cuda.synchronize(device)
            t_start = time.perf_counter()
            f(*args, **kwargs)
            torch.cuda.synchronize(device)
            return (time.perf_counter() - t_start)
        # warm up
        f(*args, **kwargs)
        torch.cuda.synchronize(device)

        t_list = []
        for _ in range(n * 2):
            torch.cuda.synchronize(device)
            t_start = time.perf_counter()
            f(*args, **kwargs)
            torch.cuda.synchronize(device)
            t_list.append(time.perf_counter() - t_start)
        t_list = np.asarray(t_list)
        return t_list[n:].mean()

    def cal_blocks(numel: int):
        return (numel + configure.cuda_threads - 1) // configure.cuda_threads

    def get_contiguous(*args):
        ret_list = []
        for item in args:
            if isinstance(item, torch.Tensor):
                ret_list.append(item.contiguous())

            elif isinstance(item, cupy.ndarray):
                ret_list.append(cupy.ascontiguousarray(item))

            else:
                raise TypeError
        return ret_list

    def wrap_args_to_raw_kernel(device: int, *args):
        # note that the input must be contiguous
        # check device and get data_ptr from tensor
        ret_list = []
        for item in args:
            if isinstance(item, torch.Tensor):
                assert item.get_device() == device
                assert item.is_contiguous()
                ret_list.append(item.data_ptr())

            elif isinstance(item, cupy.ndarray):
                assert item.device.id == device
                assert item.flags['C_CONTIGUOUS']
                ret_list.append(item)

            else:
                raise TypeError

        return tuple(ret_list)

    class GPUMonitor(threading.Thread):
        def __init__(self, gpu_ids: list = None, interval: float = 10., output_file: str or None = None, start_now=True):
            super().__init__()
            self.gpu_ids = gpu_ids
            self.interval = interval
            self.stopped = False
            self.output_file = output_file

            self.cmds = 'nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv'
            if self.gpu_ids is not None:
                self.cmds += ' -i '
                id_str = []
                for gpu_id in self.gpu_ids:
                    id_str.append(str(gpu_id))
                self.cmds += ','.join(id_str)

            if start_now:
                self.start()

        def stop(self):
            self.stopped = True

        def run(self):
            while not self.stopped:
                with os.popen(self.cmds) as fp:
                    outputs = fp.read()
                    if self.output_file is not None:
                        with open(self.output_file, 'a+', encoding='utf-8') as output_file:
                            output_file.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '\n')
                            output_file.write(outputs)
                    else:
                        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        print(outputs)

                time.sleep(self.interval)






except BaseException as e:
    print('spikingjelly.clock_driven.cu_kernel_opt:', e)
    pass