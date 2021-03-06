from __future__ import division

import numpy as np

def standardise_volumes(volumes):
    """Creates a standardised dataset (mean = 0, s.d. = 1)."""

    # Accumulate sums required for mean/s.d. calculations, as well as a point
    # count.
    intensity_sum = np.uint64(0)
    squared_intensity_sum = np.uint64(0)
    point_count = np.uint64(0)

    # Iterate through all volumes to obtain these sums, using the correct
    # uint64 type to avoid overflow.
    for volume in volumes:
        current_mri_data = volume.mri_data.astype('uint64')
        intensity_sum += np.sum(current_mri_data)
        squared_intensity_sum += np.sum(current_mri_data**2)
        point_count += current_mri_data.size

    # Calculate mean and variance from the relevant sums.
    overall_mean = intensity_sum / point_count
    overall_std = \
        np.sqrt(squared_intensity_sum / point_count - overall_mean**2)

    # Cast these values to float32 so that the transformed arrays fit into
    # memory.
    overall_mean = overall_mean.astype('float32')
    overall_std = overall_std.astype('float32')

    # Apply transformation to standardise data.
    for volume in volumes:
        volume.mri_data = volume.mri_data - overall_mean
        volume.mri_data = volume.mri_data / overall_std


def dice_coefficient(first_array, second_array):

    # Check the array dimensions match.
    if first_array.shape != second_array.shape:
        raise Exception('Array dimensions do not match.')

    # Find the number of nonzero points the arrays have in common.
    intersection_count = np.count_nonzero(
        np.logical_and(first_array, second_array))

    # Find the number of elements in the union of the array's nonzero points.
    union_count = np.count_nonzero(first_array) + \
                  np.count_nonzero(second_array)

    return 2 * intersection_count / union_count


def prediction_stats(ground_truth, prediction):
    """Find basic prediction statistics on voxel counts."""

    correct_positives = np.count_nonzero(
        np.logical_and(ground_truth == 1, prediction == 1))
    false_positives = np.count_nonzero(
        np.logical_and(ground_truth == 0, prediction == 1))
    false_negatives = np.count_nonzero(
        np.logical_and(ground_truth == 1, prediction == 0))

    return correct_positives, false_positives, false_negatives