import numpy as np
from ctypes import POINTER, c_int64
from pyTDFSDK.ctypes_data_structures import *
from pyTDFSDK.error import throw_last_timsdata_error
from pyTDFSDK.util import call_conversion_func


def tims_ccs_to_oneoverk0_for_mz(tdf_sdk, ccs, charge, mz):
    """
    Convert collisional cross section (CCS) values to 1/K0 values based on a feature's m/z value and charge.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param ccs: Collisional cross section (CCS) value of the feature.
    :type ccs: float
    :param charge: Charge of the feature.
    :type charge: int
    :param mz: m/z value of the feature.
    :type mz: float
    :return: 1/K0 value calculated from the provided feature.
    :rtype: float
    """
    return tdf_sdk.tims_ccs_to_oneoverk0_for_mz(ccs, charge, mz)


def tims_close(tdf_sdk, handle, conn):
    """
    Close TDF dataset.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param handle: Handle value for TDF dataset initialized using pyTDFSDK.tims.tims_open().
    :type handle: int
    :param conn: SQL database connection to analysis.tdf.
    :type conn: sqlite3.Connection
    :return: Tuple of the handle and connection.
    :rtype: tuple
    """
    if handle is not None:
        tdf_sdk.tims_close(handle)
        handle = None
    if conn is not None:
        conn.close()
        conn = None
    return handle, conn


def tims_extract_centroided_spectrum_for_frame_ext(tdf_sdk,
                                                   handle,
                                                   frame_id,
                                                   scan_begin,
                                                   scan_end,
                                                   peak_picker_resolution):
    """
    Read peak picked spectra for a frame from a TIMS (TDF) dataset with a custom peak picker resolution. Same as
    pyTDFSDK.tims.tims_extract_centroided_spectrum_for_frame_v2() but with a user supplied resolution for the peak
    picker.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param handle: Handle value for TDF dataset initialized using pyTDFSDK.tims.tims_open().
    :type handle: int
    :param frame_id: ID of the frame of interest.
    :type frame_id: int
    :param scan_begin: Beginning scan number (corresponding to 1/K0 value) within frame.
    :type scan_begin: int
    :param scan_end: Ending scan number (corresponding to 1/K0 value) within frame (non-inclusive).
    :type scan_end: int
    :param peak_picker_resolution: User supplied resolution for peak picker.
    :type peak_picker_resolution: int
    :return: Tuple containing an array of m/z values and an array of detector counts or 0 on error.
    :rtype: tuple[numpy.array] | int
    """
    result = None

    @MSMS_SPECTRUM_FUNCTOR
    def callback_for_dll(precursor_id, num_peaks, mz_values, area_values):
        nonlocal result
        result = (mz_values[0:num_peaks], area_values[0:num_peaks])

    rc = tdf_sdk.tims_extract_centroided_spectrum_for_frame_ext(handle,
                                                                frame_id,
                                                                scan_begin,
                                                                scan_end,
                                                                peak_picker_resolution,
                                                                callback_for_dll,
                                                                None)
    if rc == 0:
        throw_last_timsdata_error(tdf_sdk)
    return result


def tims_extract_centroided_spectrum_for_frame_v2(tdf_sdk, handle, frame_id, scan_begin, scan_end):
    """
    Read peak picked spectra for a frame from a TIMS (TDF) dataset.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param handle: Handle value for TDF dataset initialized using pyTDFSDK.tims.tims_open().
    :type handle: int
    :param frame_id: ID of the frame of interest.
    :type frame_id: int
    :param scan_begin: Beginning scan number (corresponding to 1/K0 value) within frame.
    :type scan_begin: int
    :param scan_end: Ending scan number (corresponding to 1/K0 value) within frame (non-inclusive).
    :type scan_end: int
    :return: Tuple containing an array of m/z values and an array of detector counts or 0 on error.
    :rtype: tuple[numpy.array] | int
    """
    result = None

    @MSMS_SPECTRUM_FUNCTOR
    def callback_for_dll(precursor_id, num_peaks, mz_values, area_values):
        nonlocal result
        result = (mz_values[0:num_peaks], area_values[0:num_peaks])

    rc = tdf_sdk.tims_extract_centroided_spectrum_for_frame_v2(handle,
                                                               frame_id,
                                                               scan_begin,
                                                               scan_end,
                                                               callback_for_dll,
                                                               None)
    if rc == 0:
        throw_last_timsdata_error(tdf_sdk)
    return result


def tims_extract_chromatograms(tdf_sdk, handle, jobs, trace_sink):
    """
    Extract several (MS1-only) chromatograms from an analysis.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param handle: Handle value for TDF dataset initialized using pyTDFSDK.tims.tims_open().
    :param jobs: Chromatogram definitions that will be iterated through using the generator function defined in this
        function.
    :param trace_sink: Sink callback from TDF-SDK.
    """
    @CHROMATOGRAM_JOB_GENERATOR
    def wrap_gen(job, user_data):
        try:
            job[0] = next(jobs)
            return 1
        except StopIteration:
            return 2
        except Exception as e:
            print('extract_chromatograms: generator produced exception ', e)
            return 0

    @CHROMATOGRAM_TRACE_SINK
    def wrap_sink(job_id, num_points, frame_ids, values, user_data):
        try:
            trace_sink(job_id,
                       np.array(frame_ids[0:num_points], dtype=np.int64),
                       np.array(values[0:num_points], dtype=np.uint64))
            return 1
        except Exception as e:
            print('extract_chromatograms: sink produced exception ', e)
            return 0

    unused_user_data = 0
    rc = tdf_sdk.tims_extract_chromatogram(handle, wrap_gen, wrap_sink, unused_user_data)
    if rc == 0:
        throw_last_timsdata_error(tdf_sdk)


def tims_extract_profile_for_frame(tdf_sdk, handle, frame_id, scan_begin, scan_end):
    """
    Read quasi profile spectra for a frame from a TIMS (TDF) dataset. This function sums the corresponding scan number
    ranges into a synthetic profile spectrum.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param handle: Handle value for TDF dataset initialized using pyTDFSDK.tims.tims_open().
    :type handle: int
    :param frame_id: ID of the frame of interest.
    :type frame_id: int
    :param scan_begin: Beginning scan number (corresponding to 1/K0 value) within frame.
    :type scan_begin: int
    :param scan_end: Ending scan number (corresponding to 1/K0 value) within frame (non-inclusive).
    :type scan_end: int
    :return: Array of detector counts or 0 on error.
    :rtype: numpy.array | int
    """
    result = None

    @MSMS_PROFILE_SPECTRUM_FUNCTOR
    def callback_for_dll(precursor_id, num_points, intensity_values):
        nonlocal result
        result = intensity_values[0:num_points]

    rc = tdf_sdk.tims_extract_profile_for_frame(handle, frame_id, scan_begin, scan_end, callback_for_dll, None)
    if rc == 0:
        throw_last_timsdata_error(tdf_sdk)
    return result


def tims_has_recalibrated_state(tdf_sdk, handle):
    """
    Check if the raw data has been recalibrated after acquisition (i.e. in the Bruker DataAnalysis software). Note that
    masses and 1/K0 values in the raw data SQLite files are always in the raw calibration state, not the recalibrated
    state.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param handle: Handle value for TDF dataset initialized using pyTDFSDK.tims.tims_open().
    :type handle: int
    :return: 1 if the raw data has been recalibrated after acquisition or 0 if not.
    :rtype: int
    """
    return tdf_sdk.tims_has_recalibrated_state(handle)


def tims_index_to_mz(tdf_sdk, handle, frame_id, indices):
    """
    Convert (possibly non-integer) index values for the mass dimension to m/z values.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param handle: Handle value for TDF dataset initialized using pyTDFSDK.tims.tims_open().
    :type handle: int
    :param frame_id: ID of the frame of interest.
    :type frame_id: int
    :param indices: Array of index values to be converted to m/z values.
    :type indices: numpy.array
    :return: Array of m/z values.
    :rtype: numpy.array
    """
    func = tdf_sdk.tims_index_to_mz
    return call_conversion_func(tdf_sdk, handle, frame_id, indices, func)


def tims_mz_to_index(tdf_sdk, handle, frame_id, mzs):
    """
    Convert m/z values to (possibly non-integer) index values for the mass dimension.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param handle: Handle value for TDF dataset initialized using pyTDFSDK.tims.tims_open().
    :type handle: int
    :param frame_id: ID of the frame of interest.
    :type frame_id: int
    :param mzs: Array of m/z values to be converted to index values.
    :type mzs: numpy.array
    :return: Array of index values.
    :rtype: numpy.array
    """
    func = tdf_sdk.tims_mz_to_index
    return call_conversion_func(tdf_sdk, handle, frame_id, mzs, func)


def tims_oneoverk0_to_ccs_for_mz(tdf_sdk, ook0, charge, mz):
    """
    Convert 1/K0 values to collisional cross section values (in Anstrom^2) using the Mason-Shamp equation.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param ook0: 1/K0 value of the feature to be converted.
    :type ook0: float
    :param charge: Charge of the feature to be converted.
    :type charge: int
    :param mz: m/z value of the feature to be converted.
    :type mz: float
    :return: Collisional cross section value in Angstrom^2.
    :rtype: float
    """
    return tdf_sdk.tims_oneoverk0_to_ccs_for_mz(ook0, charge, mz)


def tims_oneoverk0_to_scannum(tdf_sdk, handle, frame_id, mobilities):
    """
    Convert 1/K0 values to (possibly non-integer) scan numbers for the mobility dimension.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param handle: Handle value for TDF dataset initialized using pyTDFSDK.tims.tims_open().
    :type handle: int
    :param frame_id: ID of the frame of interest.
    :type frame_id: int
    :param mobilities: Array of 1/K0 values to be converted to scan numbers.
    :type mobilities: numpy.array
    :return: Array of scan numbers.
    :rtype: numpy.array
    """
    func = tdf_sdk.tims_oneoverk0_to_scannum
    return call_conversion_func(tdf_sdk, handle, frame_id, mobilities, func)


def tims_open(tdf_sdk, bruker_d_folder_name, use_recalibrated_state=True):
    """
    Open TDF dataset and return a non-zero instance handle to be passed to subsequent API calls.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param bruker_d_folder_name: Path to a Bruker .d file containing analysis.tdf.
    :type bruker_d_folder_name: str
    :param use_recalibrated_state: Whether to use recalibrated data (True) or not (False), defaults to True.
    :type use_recalibrated_state: bool
    :return: Non-zero instance handle.
    :rtype: int
    """
    handle = tdf_sdk.tims_open(bruker_d_folder_name.encode('utf-8'), 1 if use_recalibrated_state else 0)
    return handle


def tims_open_v2(tdf_sdk, bruker_d_folder_name, pressure_compensation_strategy, use_recalibrated_state=True):
    """
    Open TDF dataset while taking into account the pressure compensation strategy and return a non-zero instance handle
    to be passed to subsequent API calls.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param bruker_d_folder_name: Path to a Bruker .d file containing analysis.tdf.
    :type bruker_d_folder_name: str
    :param pressure_compensation_strategy: Pressure compensation strategy chosen from
        pyTDFSDK.ctypes_data_structures.PressureCompensationStrategy, either NoPressureCompensation,
        AnalysisGlobalPressureCompensation, or PerFramePressureCompensation.
    :type pressure_compensation_strategy: enum.Enum
    :param use_recalibrated_state: Whether to use recalibrated data (True) or not (False), defaults to True.
    :type use_recalibrated_state: bool
    :return: Non-zero instance handle.
    :rtype: int
    """
    handle = tdf_sdk.tims_open_v2(bruker_d_folder_name.encode('utf-8'),
                                  1 if use_recalibrated_state else 0,
                                  pressure_compensation_strategy.value)
    return handle


def tims_read_pasef_msms(tdf_sdk, handle, precursor_list):
    """
    Read peak picked MS/MS spectra for a list of PASEF precursors from a TIMS (TDF) dataset. This function reads all
    necessary PASEF frames, sums up the correspoonding scan number ranges into synthetic profile spectra for each
    precursor, performs centroiding using an algorithm and parameters suggested by Bruker, and returns the resulting
    MS/MS spectra (one for each precursor). The order of the returned MS/MS spectra does not necessarily match the
    order in the specified precursor list.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param handle: Handle value for TDF dataset initialized using pyTDFSDK.tims.tims_open().
    :type handle: int
    :param precursor_list: List of precursor IDs to obtain spectra for.
    :type precursor_list: list[int] | numpy.array
    :return: Dictionary in which the key corresponds to the precursor ID and the value is a tuple of an array of m/z
        values and an array of detector counts or 0 on error.
    :rtype: dict | int
    """
    precursors_for_dll = np.array(precursor_list, dtype=np.int64)
    result = {}

    @MSMS_SPECTRUM_FUNCTOR
    def callback_for_dll(precursor_id, num_peaks, mz_values, area_values):
        result[precursor_id] = (mz_values[0:num_peaks], area_values[0:num_peaks])

    rc = tdf_sdk.tims_read_pasef_msms(handle,
                                      precursors_for_dll.ctypes.data_as(POINTER(c_int64)),
                                      len(precursor_list),
                                      callback_for_dll)
    if rc == 0:
        throw_last_timsdata_error(tdf_sdk)
    return result


def tims_read_pasef_msms_for_frame(tdf_sdk, handle, frame_id):
    """
    Read peak picked MS/MS spectra for all PASEF precursors in a given frame from a TIMS (TDF) dataset. This function
    reads all contained PASEF precursors for a frame from the necessary PASEF frames in the same way as
    pyTDFSDK.tims.tims_read_pasef_msms(). The order of the returned MS/MS does not necessarily match the order in the
    specified precursor ID list.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param handle: Handle value for TDF dataset initialized using pyTDFSDK.tims.tims_open().
    :type handle: int
    :param frame_id: ID of the frame of interest.
    :type frame_id: int
    :return: Dictionary in which the key corresponds to the precursor ID and the value is a tuple of an array of m/z
        values and an array of detector counts or 0 on error.
    :rtype: dict | int
    """
    result = {}

    @MSMS_SPECTRUM_FUNCTOR
    def callback_for_dll(precursor_id, num_peaks, mz_values, area_values):
        result[precursor_id] = (mz_values[0:num_peaks], area_values[0:num_peaks])

    rc = tdf_sdk.tims_read_pasef_msms_for_frame(handle, frame_id, callback_for_dll)
    if rc == 0:
        throw_last_timsdata_error(tdf_sdk)
    return result


def tims_read_pasef_msms_for_frame_v2(tdf_sdk, handle, frame_id):
    """
    Read peak picked MS/MS spectra for all PASEF precursors in a given frame from a TIMS (TDF) dataset. This function
    reads all contained PASEF precursors for a frame from the necessary PASEF frames in the same way as
    pyTDFSDK.tims.tims_read_pasef_msms(). The order of the returned MS/MS does not necessarily match the order in the
    specified precursor ID list.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param handle: Handle value for TDF dataset initialized using pyTDFSDK.tims.tims_open().
    :type handle: int
    :param frame_id: ID of the frame of interest.
    :type frame_id: int
    :return: Dictionary in which the key corresponds to the precursor ID and the value is a tuple of an array of m/z
        values and an array of detector counts or 0 on error.
    :rtype: dict | int
    """
    result = {}

    @MSMS_SPECTRUM_FUNCTOR
    def callback_for_dll(precursor_id, num_peaks, mz_values, area_values):
        nonlocal result
        result[precursor_id] = (mz_values[0:num_peaks], area_values[0:num_peaks])

    rc = tdf_sdk.tims_read_pasef_msms_for_frame_v2(handle, frame_id, callback_for_dll, None)
    if rc == 0:
        throw_last_timsdata_error(tdf_sdk)
    return result


def tims_read_pasef_msms_v2(tdf_sdk, handle, precursor_list):
    """
    Read peak picked MS/MS spectra for a list of PASEF precursors from a TIMS (TDF) dataset. This function reads all
    necessary PASEF frames, sums up the correspoonding scan number ranges into synthetic profile spectra for each
    precursor, performs centroiding using an algorithm and parameters suggested by Bruker, and returns the resulting
    MS/MS spectra (one for each precursor). The order of the returned MS/MS spectra does not necessarily match the
    order in the specified precursor list.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param handle: Handle value for TDF dataset initialized using pyTDFSDK.tims.tims_open().
    :type handle: int
    :param precursor_list: List of precursor IDs to obtain spectra for.
    :type precursor_list: list[int] | numpy.array
    :return: Dictionary in which the key corresponds to the precursor ID and the value is a tuple of an array of m/z
        values and an array of detector counts or 0 on error.
    :rtype: dict | int
    """
    precursors_for_dll = np.array(precursor_list, dtype=np.int64)
    result = {}

    @MSMS_SPECTRUM_FUNCTOR
    def callback_for_dll(precursor_id, num_peaks, mz_values, area_values):
        nonlocal result
        result[precursor_id] = (mz_values[0:num_peaks], area_values[0:num_peaks])

    rc = tdf_sdk.tims_read_pasef_msms_v2(handle,
                                         precursors_for_dll.ctypes.data_as(POINTER(c_int64)),
                                         len(precursor_list),
                                         callback_for_dll,
                                         None)
    if rc == 0:
        throw_last_timsdata_error(tdf_sdk)
    return result


def tims_read_pasef_profile_msms(tdf_sdk, handle, precursor_list):
    """
    Read quasi profile MS/MS spectra for a list of PASEF precursors from a TIMS (TDF) dataset. This function reads all
    necessary PASEF frames, sums up the corresponding scan number ranges into synthetic profile spectra for each
    precursor and returns the resulting quasi profile MS/MS spectra (one for each precursor). The order of the returned
    MS/MS spectra does not necessarily match the order in the specified precursor ID list.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param handle: Handle value for TDF dataset initialized using pyTDFSDK.tims.tims_open().
    :type handle: int
    :param precursor_list: List of precursor IDs to obtain spectra for.
    :type precursor_list: list[int] | numpy.array
    :return: Dictionary in which the key corresponds to the precursor ID and the value an array of detector counts or 0
        on error.
    :rtype: dict | int
    """
    precursors_for_dll = np.array(precursor_list, dtype=np.int64)
    result = {}

    @MSMS_PROFILE_SPECTRUM_FUNCTOR
    def callback_for_dll(precursor_id, num_points, intensity_values):
        result[precursor_id] = intensity_values[0:num_points]

    rc = tdf_sdk.tims_read_pasef_profile_msms(handle,
                                              precursors_for_dll.ctypes.data_as(POINTER(c_int64)),
                                              len(precursor_list),
                                              callback_for_dll)
    if rc == 0:
        throw_last_timsdata_error(tdf_sdk)
    return result


def tims_read_pasef_profile_msms_for_frame(tdf_sdk, handle, frame_id):
    """
    Read quasi profile MS/MS spectra for all PASEF precursors in a given frame from a TIMS (TDF) dataset. This function
    reads all contained PASEF precursors for a frame from the necessary PASEF frames in the same way as
    pyTDFSDK.tims.tims_read_pasef_profile_msms(). The order of the returned MS/MS does not necessarily match the order
    in the specified precursor ID list.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param handle: Handle value for TDF dataset initialized using pyTDFSDK.tims.tims_open().
    :type handle: int
    :param frame_id: ID of the frame of interest.
    :type frame_id: int
    :return: Dictionary in which the key corresponds to the precursor ID and the value an array of detector counts or 0
        on error.
    :rtype: dict | int
    """
    result = {}

    @MSMS_PROFILE_SPECTRUM_FUNCTOR
    def callback_for_dll(precursor_id, num_points, intensity_values):
        result[precursor_id] = intensity_values[0:num_points]

    rc = tdf_sdk.tims_read_pasef_profile_msms_for_frame(handle, frame_id, callback_for_dll)
    if rc == 0:
        throw_last_timsdata_error(tdf_sdk)
    return result


def tims_read_pasef_profile_msms_for_frame_v2(tdf_sdk, handle, frame_id):
    """
    Read quasi profile MS/MS spectra for all PASEF precursors in a given frame from a TIMS (TDF) dataset. This function
    reads all contained PASEF precursors for a frame from the necessary PASEF frames in the same way as
    pyTDFSDK.tims.tims_read_pasef_profile_msms(). The order of the returned MS/MS does not necessarily match the order
    in the specified precursor ID list.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param handle: Handle value for TDF dataset initialized using pyTDFSDK.tims.tims_open().
    :type handle: int
    :param frame_id: ID of the frame of interest.
    :type frame_id: int
    :return: Dictionary in which the key corresponds to the precursor ID and the value an array of detector counts or 0
        on error.
    :rtype: dict | int
    """
    result = {}

    @MSMS_PROFILE_SPECTRUM_FUNCTOR
    def callback_for_dll(precursor_id, num_points, intensity_values):
        nonlocal result
        result[precursor_id] = intensity_values[0:num_points]

    rc = tdf_sdk.tims_read_pasef_profile_msms_for_frame_v2(handle, frame_id, callback_for_dll, None)
    if rc == 0:
        throw_last_timsdata_error(tdf_sdk)
    return result


def tims_read_pasef_profile_msms_v2(tdf_sdk, handle, precursor_list):
    """
    Read quasi profile MS/MS spectra for a list of PASEF precursors from a TIMS (TDF) dataset. This function reads all
    necessary PASEF frames, sums up the corresponding scan number ranges into synthetic profile spectra for each
    precursor and returns the resulting quasi profile MS/MS spectra (one for each precursor). The order of the returned
    MS/MS spectra does not necessarily match the order in the specified precursor ID list.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param handle: Handle value for TDF dataset initialized using pyTDFSDK.tims.tims_open().
    :type handle: int
    :param precursor_list: List of precursor IDs to obtain spectra for.
    :type precursor_list: list[int] | numpy.array
    :return: Dictionary in which the key corresponds to the precursor ID and the value an array of detector counts or 0
        on error.
    :rtype: dict | int
    """
    precursors_for_dll = np.array(precursor_list, dtype=np.int64)
    result = {}

    @MSMS_PROFILE_SPECTRUM_FUNCTOR
    def callback_for_dll(precursor_id, num_points, intensity_values):
        nonlocal result
        result[precursor_id] = intensity_values[0:num_points]

    rc = tdf_sdk.tims_read_pasef_profile_msms_v2(handle,
                                                 precursors_for_dll.ctypes.data_as(POINTER(c_int64)),
                                                 len(precursor_list),
                                                 callback_for_dll,
                                                 None)
    if rc == 0:
        throw_last_timsdata_error(tdf_sdk)
    return result


def tims_read_scans_v2(tdf_sdk, handle, frame_id, scan_begin, scan_end, initial_frame_buffer_size=128):
    """
    Read a range of scans from a single frame. The resulting arrays are equivalent to line spectra.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param handle: Handle value for TDF dataset initialized using pyTDFSDK.tims.tims_open().
    :type handle: int
    :param frame_id: ID of the frame of interest.
    :type frame_id: int
    :param scan_begin: Beginning scan number (corresponding to 1/K0 value) within frame.
    :type scan_begin: int
    :param scan_end: Ending scan number (corresponding to 1/K0 value) within frame (non-inclusive).
    :type scan_end: int
    :param initial_frame_buffer_size: Initial number of buffer bytes necessary for the output, defaults to 128.
    :type initial_frame_buffer_size: int
    :return: List of tuples where each tuple contains an array of mass indices and array of detector counts or 0 on
        error.
    :rtype: list[tuple[numpy.array]] | int
    """
    # buffer-growing loop
    while True:
        cnt = int(initial_frame_buffer_size)
        buf = np.empty(shape=cnt, dtype=np.uint32)
        length = 4 * cnt
        required_len = tdf_sdk.tims_read_scans_v2(handle,
                                                  frame_id,
                                                  scan_begin,
                                                  scan_end,
                                                  buf.ctypes.data_as(POINTER(c_uint32)),
                                                  length)
        if required_len == 0:
            throw_last_timsdata_error(tdf_sdk)
        if required_len > length:
            if required_len > 16777216:
                # arbitrary limit for now...
                raise RuntimeError('Maximum expected frame size exceeded.')
            initial_frame_buffer_size = required_len / 4 + 1  # grow buffer
        else:
            break
    result = []
    d = scan_end - scan_begin
    for i in range(scan_begin, scan_end):
        npeaks = buf[i-scan_begin]
        indices = buf[d:d+npeaks]
        d += npeaks
        intensities = buf[d:d+npeaks]
        d += npeaks
        result.append((indices, intensities))
    return result


def tims_scannum_to_oneoverk0(tdf_sdk, handle, frame_id, scan_nums):
    """
    Convert (possibly non-integer) scan numbers for the mobility dimension to 1/K0 values.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param handle: Handle value for TDF dataset initialized using pyTDFSDK.tims.tims_open().
    :type handle: int
    :param frame_id: ID of the frame of interest.
    :type frame_id: int
    :param scan_nums: Array of scan numbers to be converted to 1/K0 values.
    :type scan_nums: numpy.array
    :return: Array of 1/K0 values.
    :rtype: numpy.array
    """
    func = tdf_sdk.tims_scannum_to_oneoverk0
    return call_conversion_func(tdf_sdk, handle, frame_id, scan_nums, func)


def tims_scannum_to_voltage(tdf_sdk, handle, frame_id, scan_nums):
    """
    Convert (possibly non-integer) scan numbers for the mobility dimension to TIMS voltages.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param handle: Handle value for TDF dataset initialized using pyTDFSDK.tims.tims_open().
    :type handle: int
    :param frame_id: ID of the frame of interest.
    :type frame_id: int
    :param scan_nums: Array of scan numbers to be converted to voltages.
    :type scan_nums: numpy.array
    :return: Array of TIMS voltages.
    :rtype: numpy.array
    """
    func = tdf_sdk.tims_scannum_to_voltage
    return call_conversion_func(tdf_sdk, handle, frame_id, scan_nums, func)


def tims_set_num_threads(tdf_sdk, num_threads):
    """
    Set the number of threads that this DLL is allowed to use internally. The index <-> m/z transformation is
    internally parallelized using OpenMP. THis call is simply forwarded to omp_set_num_threads(). This function has no
    real effect on Linux.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param num_threads: Number of threads to use (>= 1)
    :type num_threads: int
    """
    tdf_sdk.tims_set_num_threads(num_threads)


def tims_voltage_to_scannum(tdf_sdk, handle, frame_id, voltages):
    """
    Convert TIMS voltages to (possibly non-integer) scan numbers for the mobility dimension.

    :param tdf_sdk: Library initialized by pyTDFSDK.init_tdf_sdk.init_tdf_sdk_api().
    :type tdf_sdk: ctypes.CDLL
    :param handle: Handle value for TDF dataset initialized using pyTDFSDK.tims.tims_open().
    :type handle: int
    :param frame_id: ID of the frame of interest.
    :type frame_id: int
    :param voltages: Array of voltages to be converted to scan numbers.
    :type voltages: numpy.array
    :return: Array of scan numbers.
    :rtype: numpy.array
    """
    func = tdf_sdk.tims_voltage_to_scannum
    return call_conversion_func(tdf_sdk, handle, frame_id, voltages, func)
