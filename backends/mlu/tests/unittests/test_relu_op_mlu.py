# Copyright (c) 2022 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

import numpy as np
import unittest

from tests.op_test import OpTest
import paddle

paddle.enable_static()
SEED = 2021


class TestRelu(OpTest):
    def setUp(self):
        self.set_mlu()
        self.op_type = "relu"

        self.init_dtype()
        np.random.seed(SEED)
        x = np.random.rand(3, 2).astype(self.dtype)
        out = x

        self.inputs = {"X": OpTest.np_dtype_to_fluid_dtype(x)}
        self.attrs = {}
        self.outputs = {"Out": out}

    def set_mlu(self):
        self.place = paddle.CustomPlace("mlu", 0)
        self.__class__.use_custom_device = True

    def init_dtype(self):
        self.dtype = np.float32

    def test_check_output(self):
        self.check_output_with_place(self.place)


class TestReluFp16(OpTest):
    def setUp(self):
        self.set_mlu()
        self.op_type = "relu"

        self.init_dtype()
        np.random.seed(SEED)
        x = np.random.rand(3, 2).astype(self.dtype)
        out = x

        self.inputs = {"X": OpTest.np_dtype_to_fluid_dtype(x)}
        self.attrs = {}
        self.outputs = {"Out": out}

    def set_mlu(self):
        self.place = paddle.CustomPlace("mlu", 0)
        self.__class__.use_custom_device = True
        self.__class__.no_need_check_grad = True

    def init_dtype(self):
        self.dtype = np.float16

    def test_check_output(self):
        self.check_output_with_place(self.place, atol=1e-5)


class TestReluNeg(OpTest):
    def setUp(self):
        self.set_mlu()
        self.op_type = "relu"

        self.init_dtype()
        np.random.seed(SEED)
        x = np.array([0.1, -0.1, -1.0]).astype(self.dtype)
        out = np.array([0.1, 0.0, 0.0]).astype(self.dtype)

        self.inputs = {"X": OpTest.np_dtype_to_fluid_dtype(x)}
        self.attrs = {}
        self.outputs = {"Out": out}

    def set_mlu(self):
        self.place = paddle.CustomPlace("mlu", 0)
        self.__class__.use_custom_device = True

    def init_dtype(self):
        self.dtype = np.float32

    def test_check_output(self):
        self.check_output_with_place(self.place)


class TestReluNet(unittest.TestCase):
    def _test(self, run_mlu=True):
        main_prog = paddle.static.Program()
        startup_prog = paddle.static.Program()
        main_prog.random_seed = SEED
        startup_prog.random_seed = SEED
        np.random.seed(SEED)

        a_np = np.random.random(size=(32, 32)).astype("float32")
        b_np = np.random.random(size=(32, 32)).astype("float32")
        label_np = np.random.randint(2, size=(32, 1)).astype("int64")

        with paddle.static.program_guard(main_prog, startup_prog):
            a = paddle.static.data(name="a", shape=[32, 32], dtype="float32")
            b = paddle.static.data(name="b", shape=[32, 32], dtype="float32")
            label = paddle.static.data(name="label", shape=[32, 1], dtype="int64")

            sum = paddle.add(a, b)
            z = paddle.nn.functional.relu(sum)

            fc_1 = paddle.static.nn.fc(x=z, size=128)
            prediction = paddle.static.nn.fc(x=fc_1, size=2, activation="softmax")

            cost = paddle.nn.functional.cross_entropy(input=prediction, label=label)
            loss = paddle.mean(cost)
            sgd = paddle.optimizer.SGD(learning_rate=0.01)
            sgd.minimize(loss)

        if run_mlu:
            place = paddle.CustomPlace("mlu", 0)
        else:
            place = paddle.CPUPlace()

        exe = paddle.static.Executor(place)
        exe.run(startup_prog)

        print("Start run on {}".format(place))
        for epoch in range(100):

            pred_res, loss_res = exe.run(
                main_prog,
                feed={"a": a_np, "b": b_np, "label": label_np},
                fetch_list=[prediction, loss],
            )
            if epoch % 10 == 0:
                print(
                    "Epoch {} | Prediction[0]: {}, Loss: {}".format(
                        epoch, pred_res[0], loss_res
                    )
                )

        return pred_res, loss_res

    def test_mlu(self):
        cpu_pred, cpu_loss = self._test(False)
        mlu_pred, mlu_loss = self._test(True)

        np.testing.assert_allclose(mlu_pred, cpu_pred, rtol=1e-6)
        np.testing.assert_allclose(mlu_loss, cpu_loss, rtol=1e-6)


if __name__ == "__main__":
    unittest.main()
