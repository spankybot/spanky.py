import json
import re

class data_type():
    def validate(self):
        raise NotImplementedError("validate() not implemented")

class data_type_string(data_type):
    def __init__(self):
        pass

    def validate(self, data):
        return data

class data_type_list(data_type):
    def __init__(self, dlist):
        self.list = dlist

    def validate(self, data):
        if data in self.list:
            return data
        else:
            raise AttributeError("%s not found in data list" % data)

class data_type_dynamic(data_type):
    def __init__(self, parent_object):
        self.parent_object = parent_object

    def validate(self, data):
        if self.parent_object.exist_thing(data):
            return data
        else:
            raise AttributeError("%s could not be found in %s" % (data, self.parent_object.name))


class SetClearFactory():
    """
    Class that can manage data in a dictionary data type.
    All information is stored in a given dictionary, where entries will be added according to a predefined hirearchy.

    :param name: name of the root dictionary element where data is stored.
    :param description: describe the current class.
    :param data_ref: dictionary where data will be stored.
    :param data_format: declares the data types that will be used.
    :param data_hierarchy: how the data types are structured.
    :param **kwargs: each data type declared in data_format must be explicitly referenced here.
    """
    def __init__(self, name, description, data_ref, data_format, data_hierarchy=None, **kwargs):
        self.data = {}
        self.name = name
        self.format = data_format.split()
        self.kwargs = dict(kwargs)
        self.data = data_ref
        self.description = description

        if self.name not in self.data:
            self.data[self.name] = {}

        for key in kwargs:
            if key not in self.format:
                raise ValueError("Type %s not specified in data_format" % key)


        for elem in self.format:
            if elem not in kwargs:
                raise ValueError("Element %s not in kwargs" % elem)

            if not self.findWholeWord(elem)(data_hierarchy):
                raise ValueError("Element %s not in data_hierarchy" % elem)

        self.hierarchy = json.loads(data_hierarchy)

    def findWholeWord(self, w):
        return re.compile(r'\b({0})\b'.format(w), flags=re.IGNORECASE).search

    def get_data(self):
        return self.data[self.name]

    def assign_rec(self, values, validator, output):
        # Go through the validator
        for key, key_type in validator.items():
            # If a key in the validator is part of the 'to assign' values
            if key in values:
#                 print("Key: %s Value: %s" % (key, values[key]))
#                 print(json.dumps(output))

                # Check if a dictionary needs to be created
                if values[key] not in output and isinstance(key_type, dict):
                    output[values[key]] = {}
#                     print(json.dumps(storage))

                if key not in output and type(key_type) not in [dict]:
                    # Check if a list needs to be created
                    if isinstance(key_type, list):
                        output[key] = []
#                         print(json.dumps(storage))
                    else:
                        # If it's not a list or dict, just assign the value
                        output[key] = values[key]
#                         print(json.dumps(storage))

                # If it's a previously created list, append to it
                if key in output and isinstance(output[key], list):
                    if values[key] not in output[key]:
                        output[key].append(values[key])

                # If it's a dictionary, go deeper
                if isinstance(key_type, dict):
                    self.assign_rec(values, key_type, output[values[key]])

    def remove_rec(self, values, validator, output):
        for key, key_type in validator.items():
            if key in values:
                #print("Key: %s Value: %s" % (key, values[key]))
                #print(json.dumps(output))

                if values[key] in output and isinstance(key_type, dict):
                    if self.remove_rec(values, key_type, output[values[key]]) == False:
                        del output[values[key]]

                    # If the object was emptied, delete it
                    if isinstance(key_type, list) and len(output[values[key]]) == 0:
                        del output[values[key]]
                    #print(json.dumps(storage))

                if key in output and isinstance(key_type, list):
                    output[key].remove(values[key])

                    # If the array was emptied, delete it
                    if (len(output[key]) == 0):
                        del output[key]
                    #print(json.dumps(storage))
                    return True

        return False

    def add_thing(self, text):
        """
        Add data to the storage, as specified in the data hierarchy
        """
        try:
            return self._add_thing(text)
        except Exception as e:
            print(str(e))
            return str(e)

    def _add_thing(self, text):

        # Check if input is according to the format
        text = text.split()
        if len(text) != len(self.format):
            raise ValueError("Invalid format")

        # Validate the data
        valid_data = {}
        for order, element in enumerate(text):
            valid_data[self.format[order]] = self.kwargs[self.format[order]].validate(element)

        # Save before and after for comparison
        data_before = json.dumps(self.data[self.name])
        # Do the assignment by using the validated data, given hierarchy and root element
        self.assign_rec(valid_data, self.hierarchy, self.data[self.name])
        data_after = json.dumps(self.data[self.name])

        # Check if something was added
        if data_before != data_after:
            self.data.sync()
            return "Added."
        else:
            raise ValueError("Data not added, probably because there is a duplicate or the input was incorrect.")

    def del_thing(self, text):
        """

        """
        try:
            return self._del_thing(text)
        except ValueError:
            return "Could not find given value"
        except Exception as e:
            print(str(e))
            return str(e)

    def _del_thing(self, text):
        text = text.split()

        valid_data = {}
        for order, element in enumerate(text):
            valid_data[self.format[order]] = self.kwargs[self.format[order]].validate(element)

        data_before = json.dumps(self.data[self.name])
        self.remove_rec(valid_data, self.hierarchy, self.data[self.name])
        data_after = json.dumps(self.data[self.name])

        # Check if something was added
        if data_before != data_after:
            self.data.sync()
            return "Deleted. "
        else:
            raise ValueError("Data not deleted, probably because the input was not correct.")

    def get_things(self):
        return self.data[self.name]

    def list_things(self):
        """
        List the keys found in the root dictionary
        """
        try:
            return self._list_things()
        except Exception as e:
            return str(e)

    def _list_things(self):
        return list(self.data[self.name])

    def list_things_for_thing(self, text, subtype):
        """
        List keys for a given data type
        """
        try:
            return self._list_things_for_thing(text, subtype)
        except Exception as e:
            return str(e)

    def _list_things_for_thing(self, text, subtype):
        text = text.split()

        if len(text) > 1:
            raise ValueError("Only one parameter can be given.")

        valid_data = None
        for order, element in enumerate(text):
            valid_data = self.kwargs[self.format[order]].validate(element)

        if valid_data in self.data[self.name]:
            if subtype in self.data[self.name][valid_data]:
                return self.data[self.name][valid_data][subtype]
            else:
                return None
        else:
            return None

    def exist_thing(self, text):
        if text in self.data[self.name]:
            return True
        return False
