from __future__ import print_function
import numpy as np
import os.path
import pyopencl as cl
from pyopencl.elementwise import ElementwiseKernel

class Kernels():

    def __init__(self, ctx):
        self.context = ctx

        self.kernel_file = os.path.join(os.path.dirname(__file__), 'kernels', 'kernels.cl')
        self.kernels = cl.Program(ctx, open(self.kernel_file).read()).build()

        self.kernels.multiply_f32 = ElementwiseKernel(ctx,
                     "float *x, float *y, float *z",
                     "z[i] = x[i] * y[i]",
                     )

        self.kernels.multiply_int32 = ElementwiseKernel(ctx,
                     "int *x, int *y, int *z",
                     "z[i] = x[i] * y[i]",
                     )

        self.kernels.c_conj_multiply = ElementwiseKernel(ctx,
                     "cfloat_t *x, cfloat_t *y, cfloat_t *z",
                     "z[i] = cfloat_mul(cfloat_conj(x[i]),y[i]);",
                     )

        self.kernels.set_to_f = ElementwiseKernel(ctx,
            """float* array, float value""",
            """array[i] = value;""",)

        self.kernels.set_to_i = ElementwiseKernel(ctx,
            """int* array, int value""",
            """array[i] = value;""",)

        
    def c_conj_multiply(self, queue, array1, array2, out):
        if (array1.dtype == array2.dtype == out.dtype == np.complex64):
            status = self.kernels.c_conj_multiply(array1, array2, out)
        else:
            raise TypeError("Datatype of arrays is not supported")

        return status

    def multiply(self, queue, array1, array2, out):
        if array1.dtype == array2.dtype == out.dtype == np.float32:
            status = self.kernels.multiply_f32(array1, array2, out)
        elif array1.dtype == array2.dtype == out.dtype == np.int32:
            status = self.kernels.multiply_int32(array1, array2, out)
        else:
            raise TypeError("Array type is not supported")
        return status

    def rotate_image3d(self, queue, sampler, image3d,
            rotmat, array_buffer, center):

        kernel = self.kernels.rotate_image3d
        compute_units = queue.device.max_compute_units

        work_groups = (compute_units*16*8, 1, 1)

        shape = np.asarray(list(array_buffer.shape) + [np.product(array_buffer.shape)], dtype=np.int32)

        inv_rotmat = np.linalg.inv(rotmat)
        inv_rotmat16 = np.zeros(16, dtype=np.float32)
        inv_rotmat16[:9] = inv_rotmat.flatten()[:]

        _center = np.zeros(4, dtype=np.float32)
        _center[:3] = center[:]

        kernel.set_args(sampler, image3d, inv_rotmat16, array_buffer.data, _center, shape)
        status = cl.enqueue_nd_range_kernel(queue, kernel, work_groups, None)

        return status

    def fill(self, queue, array, value):
        if array.dtype == np.float32:
            status = self.kernels.set_to_f(array, np.float32(value))
        elif array.dtype == np.int32:
            status = self.kernels.set_to_i(array, np.int32(value))
        else:
            raise TypeError("Array type ({:s}) is not supported.".format(array.dtype))
        return status
