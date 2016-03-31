import theano
import theano.tensor as T
import lasagne
import datatools as dt
import volumetools as vt
import features as ft
import networks as nt


def first():
    
    data_path = dt.read_data_path()
    volume = dt.load_volume(dt.list_volumes(data_path)[0])
    volume.switch_plane('axial')

    train_vol = volume[100:150, 150:250]
    test_vol = volume[150]

    train_vol.show_slice(0)

    it = vt.BatchIterator(train_vol)

    kernel_shape = [1, 9, 9]
    it.add_feature(
        lambda volume, point: ft.patch(volume, point, kernel_shape)
    )
    it.add_feature(
        lambda volume, point: ft.intensity_mean(volume, point, kernel_shape)
    )

    # Create Theano variables for input and target minibatch.
    input_var = T.matrix('X', dtype='float64')
    target_var = T.vector('y', dtype='float64')

    batch_size = 100
    network = nt.basic((batch_size, it.get_input_size()), input_var)

    # Create loss function.
    prediction = lasagne.layers.get_output(network)
    loss = lasagne.objectives.categorical_crossentropy(prediction, target_var)
    loss = loss.mean() + \
           1e-4 * lasagne.regularization.regularize_network_params(
               network, lasagne.regularization.l2)

    # Create parameter update expressions.
    params = lasagne.layers.get_all_params(network, trainable=True)
    updates = lasagne.updates.nesterov_momentum(loss, params,
                                                learning_rate=0.01,
                                                momentum=0.9)

    # Compile training function to update parameters and returns training loss.
    train_fn = theano.function([input_var, target_var], loss, updates=updates)

    # Train network.
    training_data = it(100)
    for epoch in range(5):
        loss = 0
        length = 0
        for input_batch, target_batch in training_data:
            loss += train_fn(input_batch, target_batch)
            length += 1
            if length % 100 == 0:
                print(length, 'batches done')
                
        print("Epoch %d: Loss %g" % (epoch + 1, loss / length))

    # Use trained network for predictions.
    # Test_prediction = lasagne.layers.get_output(network, deterministic=True)
    # predict = theano.function([input_var], T.argmax(test_prediction, axis=1))


if __name__ == '__main__':

    first()