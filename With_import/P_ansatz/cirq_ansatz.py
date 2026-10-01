import cirq
import sympy
theta = sympy.Symbol('theta')
q = cirq.LineQubit.range(3)
circuit = cirq.Circuit()
circuit.append(cirq.ry(theta)(q[0]))
circuit.append(cirq.ry(theta)(q[1]))
circuit.append(cirq.ry(theta)(q[2]))
circuit.append(cirq.CNOT(q[0], q[1]))
circuit.append(cirq.CNOT(q[1], q[2]))
circuit.append(cirq.measure(q[0], key='m0'))
circuit.append(cirq.measure(q[1], key='m1'))
circuit.append(cirq.measure(q[2], key='m2'))
