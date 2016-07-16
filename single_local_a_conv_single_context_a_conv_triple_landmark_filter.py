from __future__ import division

import lasagne
import numpy as np
import nolearn.lasagne
import pecdeeplearn as pdl
import data_path
import time


# Create an experiment object to keep track of parameters and facilitate data
# loading and saving.
exp = pdl.utils.Experiment(data_path.get())
exp.create_experiment(
    'single_local_a_conv_single_context_a_conv_triple_landmark'
)
exp.add_param('num_training_volumes', 45)
exp.add_param('max_points_per_volume', 50000)
exp.add_param('margins', (40, 40, 0))
exp.add_param('local_patch_shape', [41, 41, 1])
exp.add_param('local_patch_input_shape', [1, 41, 41])
exp.add_param('context_patch_source_shape', [81, 81, 1])
exp.add_param('context_patch_target_shape', [21, 21, 1])
exp.add_param('context_patch_input_shape', [1, 21, 21])
exp.add_param('landmark_1', 'Sternal angle')
exp.add_param('landmark_2', 'Left nipple')
exp.add_param('landmark_3', 'Right nipple')
exp.add_param('local_patch_conv1_filter_size', (5, 5))
exp.add_param('local_patch_conv1_num_filters', 64)
exp.add_param('context_patch_conv1_filter_size', (5, 5))
exp.add_param('context_patch_conv1_num_filters', 64)
exp.add_param('local_patch_dense_num_units', 500)
exp.add_param('context_patch_dense_num_units', 500)
exp.add_param('landmark_1_dense_num_units', 500)
exp.add_param('landmark_2_dense_num_units', 500)
exp.add_param('landmark_3_dense_num_units', 500)
exp.add_param('batch_size', 5000)
exp.add_param('update_learning_rate', 0.0001)
exp.add_param('update_momentum', 0.9)
exp.add_param('max_epochs', 100)
exp.add_param('validation_prop', 0.2)
exp.add_param('prediction_margins', (20, 20, 20))

# List and load all volumes.
vol_list = exp.list_volumes()
for vol_name in ['VL00033', 'VL00034', 'VL00069']:
    try:
        vol_list.remove(vol_name)
        vol_list.append(vol_name)
    except ValueError:
        pass
vols = [exp.load_volume(vol) for vol in vol_list]

# Standardise the data.
pdl.utils.standardise_volumes(vols)

# Split into a training set and testing set.
training_vols = vols[:exp.params['num_training_volumes']]
testing_vols = vols[exp.params['num_training_volumes']:]

# Create training maps.
training_maps = [
    pdl.extraction.half_half_map(
        vol,
        max_points=exp.params['max_points_per_volume'],
        margins=exp.params['margins']
    )
    for vol in training_vols]

# Create an Extractor.
ext = pdl.extraction.Extractor()

# Add features.
ext.add_feature(
    feature_name='local_patch',
    feature_function=lambda volume, point:
    pdl.extraction.patch(volume, point, exp.params['local_patch_shape'])
)
ext.add_feature(
    feature_name='context_patch',
    feature_function=lambda volume, point:
    pdl.extraction.scaled_patch(volume,
                                point,
                                exp.params['context_patch_source_shape'],
                                exp.params['context_patch_target_shape'])
)
ext.add_feature(
    feature_name='landmark_1',
    feature_function=lambda volume, point:
    pdl.extraction.landmark_displacement(
        volume, point, exp.params['landmark_1'])
)
ext.add_feature(
    feature_name='landmark_2',
    feature_function=lambda volume, point:
    pdl.extraction.landmark_displacement(
        volume, point, exp.params['landmark_2'])
)
ext.add_feature(
    feature_name='landmark_3',
    feature_function=lambda volume, point:
    pdl.extraction.landmark_displacement(
        volume, point, exp.params['landmark_3'])
)

# Create the net.
net = nolearn.lasagne.NeuralNet(
    layers=[

        # Layers for the local patch.
        (lasagne.layers.InputLayer,
         {'name': 'local_patch',
          'shape': tuple([None] + exp.params['local_patch_input_shape'])}),
        (lasagne.layers.Conv2DLayer,
         {'name': 'local_patch_conv1',
          'num_filters': exp.params['local_patch_conv1_num_filters'],
          'filter_size': exp.params['local_patch_conv1_filter_size']}),
        (lasagne.layers.DenseLayer,
         {'name': 'local_patch_dense',
          'num_units': exp.params['local_patch_dense_num_units']}),

        # Layers for the context patch.
        (lasagne.layers.InputLayer,
         {'name': 'context_patch',
          'shape': tuple([None] + exp.params['context_patch_input_shape'])}),
        (lasagne.layers.Conv2DLayer,
         {'name': 'context_patch_conv1',
          'num_filters': exp.params['context_patch_conv1_num_filters'],
          'filter_size': exp.params['context_patch_conv1_filter_size']}),
        (lasagne.layers.DenseLayer,
         {'name': 'context_patch_dense',
          'num_units': exp.params['context_patch_dense_num_units']}),

        # Layers for the landmark displacement.
        (lasagne.layers.InputLayer,
         {'name': 'landmark_1', 'shape': (None, 3)}),
        (lasagne.layers.DenseLayer,
         {'name': 'landmark_1_dense',
          'num_units': exp.params['landmark_1_dense_num_units']}),
        (lasagne.layers.InputLayer,
         {'name': 'landmark_2', 'shape': (None, 3)}),
        (lasagne.layers.DenseLayer,
         {'name': 'landmark_2_dense',
          'num_units': exp.params['landmark_2_dense_num_units']}),
        (lasagne.layers.InputLayer,
         {'name': 'landmark_3', 'shape': (None, 3)}),
        (lasagne.layers.DenseLayer,
         {'name': 'landmark_3_dense',
          'num_units': exp.params['landmark_3_dense_num_units']}),

        # Layers for concatenation and output.
        (lasagne.layers.ConcatLayer,
         {'name': 'concat',
          'incomings': ['local_patch_dense', 'context_patch_dense',
                        'landmark_1_dense', 'landmark_2_dense',
                        'landmark_3_dense']}),
        (lasagne.layers.DenseLayer,
         {'name': 'output', 'num_units': 2,
          'nonlinearity': lasagne.nonlinearities.softmax}),

    ],

    # Loss function.
    objective_loss_function=lasagne.objectives.categorical_crossentropy,

    # Optimization method.
    update=lasagne.updates.nesterov_momentum,
    update_learning_rate=exp.params['update_learning_rate'],
    update_momentum=exp.params['update_momentum'],

    # Iteration options.
    max_epochs=exp.params['max_epochs'],
    train_split=nolearn.lasagne.TrainSplit(exp.params['validation_prop']),

    # Other options.
    verbose=1
)
net.initialize()

# Record information to be used for printing training progress.
total_points = np.count_nonzero(training_maps)
elapsed_training_time = 0

# Train the network using a hybrid online/mini-batch approach.
for i, (input_batch, output_batch) in enumerate(ext.iterate_multiple(
        training_vols, training_maps, exp.params['batch_size'])):

    # Train and time the process.
    iteration_start_time = time.time()
    net.fit(input_batch, output_batch)
    elapsed_training_time += time.time() - iteration_start_time

    # Print the expected time remaining.
    pdl.utils.print_progress(elapsed_training_time,
                             (i + 1) * exp.params['batch_size'],
                             total_points)

print("Training complete.\n\n")

# Record results from training.
exp.add_result('training_time', elapsed_training_time)

# Try to pickle the network (which keeps the training history), but if this is
# not possible due to the size of the net then just save the weights.
try:
    exp.pickle_network(net, 'net')
except RuntimeError:
    exp.save_network_weights(net, 'net_weights')

# Perform predictions on all testing volumes in the set.
print('Beginning predictions.\n')
prediction_start_time = time.time()
for i, testing_vol in list(enumerate(testing_vols))[-5:]:

    # Perform the prediction on the current testing volume.
    print("Predicting on volume " + testing_vol.name + ".")
    predicted_vol = ext.predict(
        net,
        testing_vol,
        exp.params['batch_size'],
        bounds=testing_vol.bounding_box(
            margins=exp.params['prediction_margins'])
    )

    # Calculate statistics for this prediction and record them.
    correct_positives, false_positives, false_negatives = \
        pdl.utils.prediction_stats(testing_vol.seg_data,
                                   predicted_vol.seg_data)
    dice = pdl.utils.dice_coefficient(testing_vol.seg_data,
                                      predicted_vol.seg_data)
    exp.add_result(testing_vol.name + '_correct_positives', correct_positives)
    exp.add_result(testing_vol.name + '_false_positives', false_positives)
    exp.add_result(testing_vol.name + '_false_negatives', false_negatives)
    exp.add_result(testing_vol.name + '_dice', dice)

    # Save the prediction for comparison.
    exp.export_nii(predicted_vol)

    # Print prediction progress.
    pdl.utils.print_progress(time.time() - prediction_start_time,
                             i + 1,
                             len(testing_vols))

# Record the parameters and results.
exp.record()