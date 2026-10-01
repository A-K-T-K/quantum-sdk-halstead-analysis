import cirq
import numpy as np
q = cirq.LineQubit.range(3)
circuit = cirq.Circuit()
circuit.append(cirq.H(q[0]))
circuit.append(cirq.cphase(np.pi/2)(q[1], q[0]))
circuit.append(cirq.cphase(np.pi/4)(q[2], q[0]))
circuit.append(cirq.H(q[1]))
circuit.append(cirq.cphase(np.pi/2)(q[2], q[1]))
circuit.append(cirq.H(q[2]))
circuit.append(cirq.SWAP(q[0], q[2]))
circuit.append(cirq.measure(q[0], key='m0'))
circuit.append(cirq.measure(q[1], key='m1'))
circuit.append(cirq.measure(q[2], key='m2'))
