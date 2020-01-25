# -*- coding: utf-8 -*-
"""
Created on Wed Oct 23 17:51:58 2019

@author: tinivella
"""


class MosfetWithDiodePlecsMdl:
    """Define python virtual twin of plecs mosfet component """

    def __init__(self):
        """The constructor."""
        self.name = 'foo'
        self.name_plecs = 'MosfetWithDiode'
        self.parameter = dict()
        self.parameter['Ron'] = 1e-6

    def load_param(self, param_dict):
        """load parameters obj in plecs simulation"""
        try:
            self.name = param_dict['Name']
            self.parameter['Ron'] = param_dict['Ron']
        except KeyError:
            pass

    def load_to_plecs(self, serverObj):
        for key, value in self.parameter.items():
            serverObj.server.plecs.set(serverObj.modelName + '/' + self.name, key, str(value))


class TurnOnDelayPlecsMdl():
    def __init__(self):
        """The constructor."""
        self.name = 'foo'
        self.name_plecs = 'Turn-on Delay'
        self.parameter = {'T_d': None}

    def load_param(self, param_dict):
        try:
            self.name = param_dict['Name']
            self.parameter['T_d'] = param_dict['T_d']
        except KeyError:
            pass

    def get_inductance(self):
        print("T is", self.parameter['T_d'])

    def load_to_plecs(self, serverObj):
        for key, value in self.parameter.items():
            serverObj.server.plecs.set(serverObj.modelName + '/' + self.name, key, str(value))


class ResistorPlecsMdl():
    def __init__(self):
        """The constructor."""
        self.name = 'foo'
        self.name_plecs = 'Resistor'
        self.parameter = dict()
        self.parameter['R'] = 1e-3

    def load_param(self, param_dict):
        try:
            self.name = param_dict['Name']
            self.parameter['R'] = param_dict['R']
        except KeyError:
            pass

    def get_inductance(self):
        print("L is", self.parameter['L'])

    def load_to_plecs(self, serverObj):
        for key, value in self.parameter.items():
            serverObj.server.plecs.set(serverObj.modelName + '/' + self.name, key, str(value))


class CapacitorPlecsMdl():
    def __init__(self):
        """The constructor."""
        self.name = 'foo'
        self.name_plecs = 'Capacitor'
        self.parameter = dict()
        self.parameter['C'] = 1e-15
        self.parameter['v_init'] = 0

    def load_param(self, param_dict):
        try:
            self.name = param_dict['Name']
            self.parameter['C'] = param_dict['C']
            self.parameter['v_init'] = param_dict['v_init']
        except KeyError:
            pass

    def get_capacitance(self):
        print("C is", self.parameter['C'])

    def load_to_plecs(self, serverObj):
        for key, value in self.parameter.items():
            serverObj.server.plecs.set(serverObj.modelName + '/' + self.name, key, str(value))


class InductorPlecsMdl():
    def __init__(self):
        """The constructor."""
        self.name = 'foo'
        self.name_plecs = 'Inductor'
        self.parameter = dict()
        self.parameter['L'] = 1e-6
        self.parameter['i_init'] = 0

    def load_param(self, param_dict):
        try:
            self.name = param_dict['Name']
            self.parameter['L'] = param_dict['L']
            self.parameter['i_init'] = param_dict['i_init']
        except KeyError:
            pass

    def get_inductance(self):
        print("L is", self.parameter['L'])

    def load_to_plecs(self, serverObj):
        for key, value in self.parameter.items():
            serverObj.server.plecs.set(serverObj.modelName + '/' + self.name, key, str(value))


class TransformerPlecsMdl():
    def __init__(self):
        """The constructor."""
        self.name = 'foo'
        self.name_plecs = 'Transformer'
        self.parameter = dict()
        self.parameter['Windings'] = [1, 1]
        self.parameter['n'] = [1, 1]
        self.parameter['Lm'] = 1e-3
        self.parameter['im0'] = 0

    def load_param(self, param_dict):
        try:
            self.name = param_dict['Name']
            self.parameter['Windings'] = param_dict['Windings']
            self.parameter['n'] = param_dict['n']
            self.parameter['Lm'] = param_dict['Lm']
            self.parameter['im0'] = param_dict['im0']
        except KeyError:
            pass

    def load_to_plecs(self, serverObj):
        for key, value in self.parameter.items():
            serverObj.server.plecs.set(serverObj.modelName + '/' + self.name, key, str(value))


def load_all_comp_to_plecs(server, componentList):
    for item in componentList:
        if item['Type'] == 'MosfetWithDiode':
            foo = MosfetWithDiodePlecsMdl()
            foo.load_param(item)
            foo.load_to_plecs(server)
        if item['Type'] == 'Resistor':
            foo = ResistorPlecsMdl()
            foo.load_param(item)
            foo.load_to_plecs(server)
        if item['Type'] == 'Capacitor':
            foo = CapacitorPlecsMdl()
            foo.load_param(item)
            foo.load_to_plecs(server)
        if item['Type'] == 'Inductor':
            foo = InductorPlecsMdl()
            foo.load_param(item)
            foo.load_to_plecs(server)
        if item['Type'] == 'Transformer':
            foo = TransformerPlecsMdl()
            foo.load_param(item)
            foo.load_to_plecs(server)
        if item['Type'] == 'Turn-on Delay':
            foo = TurnOnDelayPlecsMdl()
            foo.load_param(item)
            foo.load_to_plecs(server)
