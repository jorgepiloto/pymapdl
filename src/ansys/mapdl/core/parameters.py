import os
import tempfile
import weakref

from ansys.mapdl.reader._reader import write_array
import numpy as np

from ansys.mapdl.core.mapdl import _MapdlCore
from ansys.mapdl.core.misc import supress_logging

ROUTINE_MAP = {
    0: "Begin level",
    17: "PREP7",
    21: "SOLUTION",
    31: "POST1",
    36: "POST26",
    52: "AUX2",
    53: "AUX3",
    62: "AUX12",
    65: "AUX15",
}

UNITS_MAP = {
    -1: "NONE",
    0: "USER",
    1: "SI",
    2: "CGS",
    3: "BFT",
    4: "BIN",
    5: "MKS",
    6: "MPA",
    7: "uMKS",
}


class Parameters:
    """Collection of MAPDL parameters obtainable from the :func:`ansys.mapdl.core.Mapdl.get` command.

    Notes
    -----

    **Leading underscored parameters**

    The parameters starting with underscore ('_') are reserved parameters
    for MAPDL macros and routines, therefore its use is discouraged, and
    in PyMAPDL you cannot set them by default.

    If you need to set one of this parameters, you can use ``mapdl._run``
    to avoid PyMAPDL parameter name checks. For example

    >>> mapdl._run('_parameter=123')
    'PARAMETER _PARAMETER =     123.00000000'

    By default, this type of parameters cannot be seen when issuing
    ``mapdl.parameters``. However, you can change this by setting
    ``mapdl.parameters.show_leading_underscore_parameters`` equal to True.
    For example:

    >>> mapdl.parameters.show_leading_underscore_parameters=True
    >>> mapdl.parameters
    MAPDL Parameters
    ----------------
    PORT                             : 50053.0
    _RETURN                          : 0.0
    _STATUS                          : 0.0
    _UIQR                            : 17.0


    **Trailing underscored parameters**

    The parameters ending underscore are recommend for user routines
    and macros.
    You can set this type of parameters in PyMAPDL, but by default,
    they cannot be seen in ``mapdl.parameters``, unless
    ``mapdl.parameters.show_trailing_underscore_parameters`` is set
    to True.

    >>> mapdl.parameters['param_'] = 1.0
    >>> mapdl.parameters
    MAPDL Parameters
    ----------------
    >>> mapdl.parameters.show_trailing_underscore_parameters=True
    >>> mapdl.parameters
    MAPDL Parameters
    ----------------
    PARAM_                           : 1.0

    **Parameters with leading and trailing underscore**

    These are an especial type of parameters. They CANNOT be seen
    in ``mapdl.parameters`` under any circumstances, and because
    of it, it uses is not recommended.

    You can still retrieve them using any of the normal methods
    to retrieve parameters. But you shall know the parameter name.
    For example:

    >>> mapdl.parameters["_param_"] = 1.0
    >>> mapdl.parameters
    MAPDL Parameters
    ----------------
    >>> print(mapdl.parameters['_param_'])
    1.0

    Examples
    --------
    Simply list all parameters except for MAPDL MATH parameters.

    >>> mapdl.parameters
    ARR                              : ARRAY DIM (3, 1, 1)
    PARM_FLOAT                       : 20.0
    PARM_INT                         : 10.0
    PARM_LONG_STR                    : "stringstringstringstringstringst"
    PARM_STR                         : "string"
    PORT                             : 50052.0

    Get a parameter

    >>> mapdl.parameters['PARM_FLOAT']
    20.0

    Get an array parameter

    >>> mapdl.parameters['ARR']
    array([1., 2., 3.])

    """

    def __init__(self, mapdl):
        if not isinstance(mapdl, _MapdlCore):
            raise TypeError("Must be implemented from MAPDL class")
        self._mapdl_weakref = weakref.ref(mapdl)
        self.show_leading_underscore_parameters = False
        self.show_trailing_underscore_parameters = False
        self.full_parameters_output = self._full_parameter_output(self)

    @property
    def _mapdl(self):
        """Return the weakly referenced instance of mapdl"""
        return self._mapdl_weakref()

    def _set_log_level(self, level):
        self._mapdl.set_log_level(level)

    @property
    def _log(self):
        return self._mapdl._log

    @property
    def numcpu(self) -> int:
        """Number of Distributed MAPDL processes being used.

        Notes
        -----
        This will always return ``1`` when using shared memory parallel.

        Examples
        --------
        >>> mapdl.parameters.numcpu
        2

        """
        return int(self._mapdl.get_value("ACTIVE", item1="NUMCPU"))

    @property
    def routine(self) -> str:
        """Current routine string as a string.  For example ``"/PREP7"``

        MAPDL Command: \*GET, ACTIVE, 0, ROUT

        Returns
        -------
        routine : str
            Routine as a string.  One of:

                - ``"Begin level"``
                - ``"PREP7"``
                - ``"SOLUTION"``
                - ``"POST1"``
                - ``"POST26"``
                - ``"AUX2"``
                - ``"AUX3"``
                - ``"AUX12"``
                - ``"AUX15"``

        Examples
        --------
        >>> mapdl.parameters.routine
        'PREP7'
        """
        value = self._mapdl.get_value("ACTIVE", item1="ROUT")
        return ROUTINE_MAP[int(value)]

    @property
    def units(self) -> str:
        """Units specified by /UNITS command.

        Returns
        -------
        units : str
            Active Units.  One of:
                - ``"None"``
                - ``"USER"``
                - ``"SI"``
                - ``"CGS"``
                - ``"BFT"``
                - ``"BIN"``
                - ``"MKS``
                - ``"MPA"``
                - ``"uMKS"``

        Examples
        --------
        >>> mapdl.parameters.units
        'NONE'
        """
        value = self._mapdl.get_value("ACTIVE", item1="UNITS")
        return UNITS_MAP[int(value)]

    @property
    def revision(self) -> float:
        """MAPDL revision version.

        Examples
        --------
        >>> mapdl.parameters.revision
        20.2
        """
        return float(self._mapdl.get_value("ACTIVE", item1="REV"))

    @property
    def platform(self) -> str:
        """The current platform.

        Examples
        --------
        >>> mapdl.parameters.platform
        'LIN'
        """
        return self._mapdl.get_value("ACTIVE", item1="PLATFORM")

    @property
    def csys(self) -> int:
        """Active coordinate system

        Examples
        --------
        >>> mapdl.parameters.csys
        0
        """
        return int(self._mapdl.get_value("ACTIVE", item1="CSYS"))

    @property
    def dsys(self) -> int:
        """Active display coordinate system

        Examples
        --------
        >>> mapdl.parameters.dsys
        0
        """
        return int(self._mapdl.get_value("ACTIVE", item1="DSYS"))

    @property
    def rsys(self) -> int:
        """Active result coordinate system

        Examples
        --------
        >>> mapdl.parameters.rsys
        0
        """
        return int(self._mapdl.get_value("ACTIVE", item1="RSYS"))

    @property
    def esys(self) -> int:
        """Active element coordinate system

        Examples
        --------
        >>> mapdl.parameters.esys
        0
        """
        return int(self._mapdl.get_value("ACTIVE", item1="ESYS"))

    @property
    def section(self) -> int:
        """Active section number

        Examples
        --------
        >>> mapdl.parameters.section
        1
        """
        return int(self._mapdl.get_value("ACTIVE", item1="SECT"))

    @property
    def material(self) -> int:
        """Active material

        Examples
        --------
        >>> mapdl.parameters.material
        1
        """
        return int(self._mapdl.get_value("ACTIVE", item1="MAT"))

    @property
    def real(self) -> int:
        """Active real constant set

        Examples
        --------
        >>> mapdl.parameters.real
        1
        """
        return int(self._mapdl.get_value("ACTIVE", item1="REAL"))

    @property
    def type(self) -> int:
        """Active element type

        Examples
        --------
        >>> mapdl.parameters.type
        1
        """
        return int(self._mapdl.get_value("ACTIVE", item1="type"))

    @property
    @supress_logging
    def _parm(self):
        """Current MAPDL parameters"""
        params = interp_star_status(self._mapdl.starstatus())

        if self.show_leading_underscore_parameters:
            _params = interp_star_status(self._mapdl.starstatus("_PRM"))
            params.update(_params)

        if self.show_trailing_underscore_parameters:
            params_ = interp_star_status(self._mapdl.starstatus("PRM_"))
            params.update(params_)

        return params

    def __repr__(self):
        """Return the current parameters in a pretty format"""
        lines = ["MAPDL Parameters", "----------------"]
        for key, info in self._parm.items():
            value_str = ""
            if info["type"] == "ARRAY":
                value_str = "ARRAY DIM %s" % str(info["shape"])
            elif info["type"] == "TABLE":
                value_str = "TABLE DIM %s" % str(info["shape"])
            elif info["type"] == "CHARACTER":
                value_str = '"%s"' % info["value"]
            elif "value" in info:
                value_str = str(info["value"])
            else:
                continue
            lines.append("%-32s : %s" % (key, value_str))
        return "\n".join(lines)

    def __getitem__(self, key):
        """Return a parameter"""
        if not isinstance(key, str):
            raise TypeError("Parameter name must be a string")
        key = key.upper()

        # We are going to directly query the desired parameter.
        # It is more efficient (less parsing) and
        # you can obtain leading and trailing underscore parameters, which
        # they don't appear in a normal ``*STATUS``

        with self.full_parameters_output:
            parameters = self._parm

        if key not in parameters:
            raise IndexError("%s not a valid parameter_name" % key)

        parm = parameters[key]
        if parm["type"] in ["ARRAY", "TABLE"]:
            try:
                return self._get_parameter_array(key, parm["shape"])
            except ValueError:
                # allow a second attempt
                return self._get_parameter_array(key, parm["shape"])

        return parm["value"]

    def __setitem__(self, key, value):
        """Set a parameter"""
        self._mapdl._check_parameter_name(key)

        # parameters = self._parm  # check parameter exists
        if isinstance(value, (np.ndarray, list)):
            self._set_parameter_array(key, value)
        else:
            self._set_parameter(key, value)

    @supress_logging
    def _set_parameter(self, name, value):
        """Set a single parameter within MAPDL

        Parameters
        ----------
        name : str
            An alphanumeric name used to identify this parameter.  Name
            may be up to 32 characters, beginning with a letter and
            containing only letters, numbers, and underscores.
            Examples: ``"ABC" "A3X" "TOP_END"``.

        """
        if not isinstance(value, (str, int, float)):
            raise TypeError("``Parameter`` must be either a float, int, or string")

        if not isinstance(name, str):
            raise TypeError("``name`` must be a string")

        if len(name) > 32:
            raise ValueError("Length of ``name`` must be 32 characters or less")

        # delete the parameter if it exists as an array
        parm = self._parm
        if name in parm:
            if parm[name]["type"] == "ARRAY":
                self._mapdl.starset(name, mute=True)

        if isinstance(value, str):
            if " " in value:
                raise ValueError("Spaces not allowed in strings in MAPDL")
            self._mapdl.starset(name, f"'{value}'", mute=True)
        else:
            self._mapdl.starset(name, value, mute=True)

    @supress_logging
    def _get_parameter_array(self, parm_name, shape):
        """Return an ANSYS array parameter as a numpy.ndarray

        Parameters
        ----------
        parm_name : str
            MAPDL parameter name.

        Returns
        -------
        array : np.ndarray
            Numpy array.
        """
        escaped = False
        for each_format_number in [20, 30, 40, 64, 100]:
            format_str = f"(1F{each_format_number}.12)"
            with self._mapdl.non_interactive:
                # use C ordering
                self._mapdl.mwrite(parm_name.upper(), label="kji")
                self._mapdl.run(format_str)

            st = self._mapdl.last_response.rfind(format_str) + len(format_str) + 1

            if "**" not in self._mapdl.last_response[st:]:
                escaped = True
                break

        if not escaped:  # pragma: no cover
            raise RuntimeError(
                f"The array '{parm_name}' has a number format "
                "that could not be read using '{format_str}'."
            )

        arr_flat = np.fromstring(self._mapdl.last_response[st:], sep="\n").reshape(
            shape
        )

        if len(shape) == 3:
            if shape[2] == 1:
                arr_flat = arr_flat.squeeze(axis=2)

        return arr_flat

    @supress_logging
    def _set_parameter_array(self, name, arr):
        """Load a numpy array or python list directly to MAPDL

        Writes the numpy array to disk and then reads it in within
        MAPDL using \*VREAD.

        Parameters
        ----------
        arr : np.ndarray or List
            Array to send to MAPDL.  Maximum of 3 dimensions.

        name : str
            Name of the array to write to within MAPDL.

        Examples
        --------
        Load a 1D numpy array into MAPDL

        >>> arr = np.array([10, 20, 30])
        >>> mapdl.set_parameter_array(arr, 'MYARR')
        >>> parm, mapdl_arrays = mapdl.load_parameters()
        >>> mapdl_arrays['MYARR']
        array([10., 20., 30.])

        Load a 2D numpy array into MAPDL

        >>> arr = np.random.random((5, 3))
        >>> mapdl.set_parameter_array(arr, 'MYARR')
        >>> parm, mapdl_arrays = mapdl.load_parameters()
        >>> mapdl_arrays['MYARR']
        array([[0.39806635, 0.15060953, 0.3990557 ],
               [0.26837768, 0.02033222, 0.15655861],
               [0.46110226, 0.06381489, 0.20068533],
               [0.20122863, 0.5727896 , 0.85636037],
               [0.68126612, 0.67460878, 0.3678797 ]])

        Load a python list into MAPDL

        >>> mapdl.set_parameter_array([10, -1, 8, 4, 10], 'MYARR')
        >>> parm, mapdl_arrays = mapdl.load_parameters()
        >>> mapdl_arrays['MYARR']
        array([10., -1.,  8.,  4., 10.])

        """
        # type checks
        arr = np.array(arr)
        if not np.issubdtype(arr.dtype, np.number):
            raise TypeError("Only numerical arrays or lists are supported")
        if arr.ndim > 3:
            raise ValueError(
                "MAPDL VREAD only supports a arrays with a" " maximum of 3 dimensions."
            )

        if not isinstance(name, str):
            raise TypeError("``name`` must be a string")

        name = name.upper()

        idim, jdim, kdim = arr.shape[0], 1, 1
        if arr.ndim >= 2:
            jdim = arr.shape[1]
        if arr.ndim == 3:
            kdim = arr.shape[2]

        # 2021R1 and earlier has stability issues.  Directly stream
        # results for improved performance and stability, but up to a
        # size limit.
        if arr.size < 1000:
            return self._set_array_chain(name, arr, idim, jdim, kdim)

        # write array from numpy to disk
        filename = "_tmp.dat"
        self._write_numpy_array(filename, arr)

        cmd = f"{name}(1, 1),{filename},,,IJK,{idim},{jdim},{kdim}"
        with self._mapdl.non_interactive:
            self._mapdl.dim(name, imax=idim, jmax=jdim, kmax=kdim)
            self._mapdl.vread(cmd)
            self._mapdl.run("(1F20.12)")

    def _set_array_chain(self, name, arr, idim, jdim, kdim):
        """Sets an array using chained commands

        Faster and more stable (as of 2021R1) for small arrays.
        """
        if arr.ndim == 1:
            arr = np.expand_dims(arr, [1, 2])
        elif arr.ndim == 2:
            arr = np.expand_dims(arr, 2)

        # backwards compatibility with CORBA
        if hasattr(self._mapdl, "mute"):
            old_mute = self._mapdl.mute
            self._mapdl.mute = True

        with self._mapdl.non_interactive:
            self._mapdl.dim(name, imax=idim, jmax=jdim, kmax=kdim)
            for i in range(idim):
                for j in range(jdim):
                    for k in range(kdim):
                        index = f"{i + 1},{j + 1},{k + 1}"
                        self._mapdl.run(f"{name}({index})={arr[i, j, k]}")

        if hasattr(self._mapdl, "mute"):
            self._mapdl.mute = old_mute

    def _write_numpy_array(self, filename, arr):
        """Write a numpy array to disk"""
        if arr.dtype != np.double:
            arr = arr.astype(np.double)

        if self._mapdl._local:
            filename = os.path.join(self._mapdl.directory, filename)
        else:
            filename = os.path.join(tempfile.gettempdir(), filename)
        write_array(filename.encode(), arr.ravel("F"))

        if not self._mapdl._local:
            self._mapdl.upload(filename, progress_bar=False)

    class _full_parameter_output:
        """Change the show_** options to true to allow full parameter output."""

        def __init__(self, parent):
            self._parent = weakref.ref(parent)
            self.show_leading_underscore_parameters = None
            self.show_trailing_underscore_parameters = None

        def __enter__(self):
            """Storing current state."""
            self.show_leading_underscore_parameters = (
                self._parent().show_leading_underscore_parameters
            )
            self.show_trailing_underscore_parameters = (
                self._parent().show_trailing_underscore_parameters
            )

            # Getting full output.
            self._parent().show_leading_underscore_parameters = True
            self._parent().show_trailing_underscore_parameters = True

        def __exit__(self, *args):
            """Coming back to previous state."""
            self._parent().show_leading_underscore_parameters = (
                self.show_leading_underscore_parameters
            )
            self._parent().show_trailing_underscore_parameters = (
                self.show_trailing_underscore_parameters
            )


def interp_star_status(status):
    """Interprets \*STATUS command output from MAPDL

    Parameters
    ----------
    status : str
        Output from MAPDL *STATUS

    Returns
    -------
    parameters : dict
        Dictionary of parameters.
    """
    parameters = {}
    st = status.find("NAME                              VALUE")
    for line in status[st + 80 :].splitlines():
        items = line.split()
        if not items:
            continue

        # line will contain either a character, scalar, or array
        name = items[0]
        if len(items) == 2:
            if items[1][-9:] == "CHARACTER":
                parameters[name] = {"type": "CHARACTER", "value": items[1][:-9]}
            # else:
            # log.warning(
        elif len(items) == 3:
            if items[2] == "SCALAR":
                value = float(items[1])
            else:
                value = items[1]
            parameters[name] = {"type": items[2], "value": value}
        elif len(items) == 5:
            shape = (int(items[2]), int(items[3]), int(items[4]))
            parameters[name] = {"type": items[1], "shape": shape}
    return parameters
