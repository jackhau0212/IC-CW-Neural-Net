# revamped
from sklearn import preprocessing
from sklearn.model_selection import train_test_split
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import LabelBinarizer, StandardScaler

import torch
import pickle
import numpy as np
import pandas as pd


class Regressor():
    def __init__(self, x, learn_rate = 0.1, no_of_layers = 1, no_of_neurons = 23, nb_epoch = 1000, act_function = "tanh"):
        """ 
        Initialise the model.
          
        Arguments:
            - x {pd.DataFrame} -- Raw input data of shape (batch_size, input_shape), used to compute the size of the network.
            - nb_epoch {int} -- number of epochs to train the network.
            - learn_rate {float} -- learning rate for optimiser.
            - no_of_layers {int} -- number of hidden layers in the neuralnetwork.
            - no_of_neurons {int} -- number of neurons per hidden layer.
            - act_function {string} -- act_function function to apply after each hidden layer. "relu", "sigmoid" or "tanh".

        """
        self.x = x # for new regressor (hyperparam tuning)
        self.x_mean = None  # for saving x_mean so that it can be used for testing instances
        self.x_ocean_prox_mode = None
        self.y_min = None  # for testing 
        self.y_max = None  # for testing 

        # init attributes required for preprocessor only
        self.lb_ocean_prox = preprocessing.LabelBinarizer()  # label binarizer
        self.x_min_max_scaled = preprocessing.MinMaxScaler()  # minmax scaler for x
        self.y_min_max_scaled = preprocessing.MinMaxScaler()  # minmax scaler for y
        self.standardiser = StandardScaler()
        self.lb = LabelBinarizer()

        X, _ = self._preprocessor(x, training = True)
        self.input_shape = X.shape[1]
        self.output_shape = 1
        self.nb_epoch = nb_epoch
        self.learn_rate = learn_rate
        self.no_of_layers = no_of_layers
        self.no_of_neurons = no_of_neurons
        self.act_function = act_function
        self.model = self.Model(self.input_shape, self.output_shape, self.no_of_layers, self.no_of_neurons, self.act_function)
    
    def fit(self, x, y):
        """
        Regressor training function

        Arguments:
            - x {pd.DataFrame} -- Raw input array of shape 
                (batch_size, input_shape).
            - y {pd.DataFrame} -- Raw output array of shape (batch_size, 1).

        Returns:
            self {Regressor} -- Trained model.

        """
        #######################################################################
        #                       ** START OF YOUR CODE **
        #######################################################################
        
        X, Y = self._preprocessor(x, y = y, training = True)

        loss = torch.nn.MSELoss()
        optimiser = torch.optim.Adam(self.model.parameters(), lr=self.learn_rate)

        for _ in range(self.nb_epoch):
            optimiser.zero_grad()
            predictions = self.model.forward(X)
            mse_loss = loss.forward(input=predictions, target=Y)
            mse_loss.backward()
            optimiser.step()
        
        return self

        #######################################################################
        #                       ** END OF YOUR CODE **
        #######################################################################

    def _preprocessor(self, x, y = None, training = False):
        """ 
        Preprocess input of the network.
          
        Arguments:
            - x {pd.DataFrame} -- Raw input array of shape 
                (batch_size, input_size).
            - y {pd.DataFrame} -- Raw target array of shape (batch_size, 1).
            - training {boolean} -- Boolean indicating if we are training or 
                testing the model.

        Returns:
            - {torch.tensor} or {numpy.ndarray} -- Preprocessed input array of
              size (batch_size, input_size). The input_size does not have to be the same as the input_size for x above.
            - {torch.tensor} or {numpy.ndarray} -- Preprocessed target array of
              size (batch_size, 1).
            
        """

        #######################################################################
        #                       ** START OF YOUR CODE **
        #######################################################################
        
        # Columns with categorical data in a list
        non_float_cols = [col for col in x.columns if x[col].dtype == "object"]
        
        # Separate data into categorical and numerical
        categorical_data = x[non_float_cols]
        numerical_data = x.drop(non_float_cols, axis = 1)
        
        # Fill empty values with random variables
        empty_filled_numerica_data = self.fill_empty_labels(numerical_data)

        # Standardisation
        if training: # Training data fits onto the standardiser model
            self.standardiser.fit(empty_filled_numerica_data)
            standardised_x = pd.DataFrame(self.standardiser.transform(empty_filled_numerica_data), columns = empty_filled_numerica_data.columns)
        else: # Testing data uses the standardiser model from training (it cannot fit onto the model)
            standardised_x = pd.DataFrame(self.standardiser.transform(empty_filled_numerica_data), columns = empty_filled_numerica_data.columns)
        
        # One Hot Encoding with LabelBinarizer
        one_hot_encoded_data = self.one_hot_encode(categorical_data, non_float_cols)
        
        # Concatenate the categorical and numerical data
        preprocess_data = pd.concat([standardised_x, one_hot_encoded_data], axis = 1)
        
        # Return preprocessed x and y, return None for y if it was None
        return torch.tensor(preprocess_data.values, dtype=torch.float32), (torch.tensor(y.values, dtype=torch.float32) if isinstance(y, pd.DataFrame) else None)

        
        #######################################################################
        #                       ** END OF YOUR CODE **
        #######################################################################


    # Correct empty feature instances with a normally distributed random variable using the feature mean and standard deviation
    def fill_empty_labels(self, raw_input):
        """
        Fill in the empty values of the raw input with a random variable 
        using the mean and standard deviation of the label

        Args:
            raw_input (pandas dataframe): dataframe containing the raw input data

        Returns:
            _type_: all nan are filled with random variables
        """
        for label in raw_input.columns: # loop for all labels
            if raw_input[label].dtype == 'object': # if label is not a float, skip
                mask = raw_input[label].isnull() # find where empty values exist
                num_empty = mask.sum()
                
                if num_empty > 0: # if empty values detected
                    raw_input.loc[mask, label] = raw_input[label].mode() # assign a random value to each of the empty values
            else:
                mean = raw_input[label].mean() # label mean 
                std_dev = raw_input[label].std() # label std dev
                mask = raw_input[label].isnull() # find where empty values exist
                num_empty = mask.sum()
            
                if num_empty > 0: # if empty values detected
                    random_values = np.random.normal(mean, std_dev, size=num_empty).astype(int) # generate a list of varying random variables
                    random_values[random_values < 0] = 0 # only total_bedrooms has empty values, ensure values are positive whole numbers
                    
                    raw_input.loc[mask, label] = random_values # assign a random value to each of the empty values
                
        return raw_input
    
    # One hot encode the categorical data
    def one_hot_encode(self, raw_input, non_float_cols):
        """
        One hot encode the categorical data

        Args:
            raw_input (pandas dataframe): dataframe containing the raw input data
            non_float_cols (list): list of all non float columns

        Returns:
            _type_: all categorical data is one hot encoded
        """
        if len(non_float_cols) != 0:
            
            encoded_dict = {}
            
            for non_float_col in non_float_cols:
                self.lb.fit(raw_input[non_float_col])
                
                encoded = self.lb.fit_transform(raw_input[non_float_col])

                for i, unique_label in enumerate(raw_input[non_float_col].unique()):
                    feature = "is_" + str(unique_label)
                    
                    encoded_dict[feature] = encoded[:, i]
            
            # Initialise the one_hot_encoded_data dataframe
            one_hot_encoded_data = pd.DataFrame(encoded_dict, columns=encoded_dict.keys())
            
            return one_hot_encoded_data
        else:
            return None
    

    def predict(self, x):
        """
        Output the value corresponding to an input x.

        Arguments:
            x {pd.DataFrame} -- Raw input array of shape 
                (batch_size, input_shape).

        Returns:
            {np.ndarray} -- Predicted value for the given input (batch_size, 1).
        """
        #######################################################################
        #                       ** START OF YOUR CODE **
        #######################################################################

        with torch.no_grad():
            X, _ = self._preprocessor(x, training = False) # Do not forget
            output = self.model.forward(X)
            output = self._postprocessor(output)
            return np.array(output)

        #######################################################################
        #                       ** END OF YOUR CODE **
        #######################################################################


    def score(self, x, y):
        """
        Function to evaluate the model accuracy on a validation dataset.

        Arguments:
            - x {pd.DataFrame} -- Raw input array of shape 
                (batch_size, input_shape).
            - y {pd.DataFrame} -- Raw output array of shape (batch_size, 1).

        Returns:
            {float} -- Quantification of the efficiency of the model.

        """

        with torch.no_grad():
            X, Y = self._preprocessor(x, y = y, training = False) # Do not forget
            predictions = self.model.forward(X)
            return mean_squared_error(np.array(y), np.array(predictions), squared=False)


    # Functions to make Regressor comply with GridSearchCV
    def get_params(self, deep=False):
        # return current paramater to the GridSearch
        return {"no_of_layers":self.no_of_layers, "no_of_neurons":self.no_of_neurons, "act_function":self.act_function, "x":self.x,
        "nb_epoch":self.nb_epoch, "learn_rate":self.learn_rate}

    def set_params(self, **parameters):
        # let GridSearch set new params
        for parameter, value in parameters.items():
            setattr(self, parameter, value)
        return self


    # Inner class defining the neural network
    class Model(torch.nn.Module):
        def __init__(self, input_shape, output_shape, no_of_layers, no_of_neurons, act_function):
            super().__init__()

            self.input_shape = input_shape
            self.output_shape = output_shape
            self.no_of_layers = no_of_layers
            self.no_of_neurons = no_of_neurons
            self.act_function = act_function

            ### Create layers of neural network
            # Input layer 
            self.input_layer = torch.nn.Linear(in_features=self.input_shape, out_features=self.no_of_neurons)
            # Hidden layers
            if self.no_of_layers > 1:
                self.hidden_layers = torch.nn.ModuleList([torch.nn.Linear(in_features=self.no_of_neurons, out_features=self.no_of_neurons) for _ in range(self.no_of_layers-1)])
            # Output layer
            self.output_layer = torch.nn.Linear(in_features=self.no_of_neurons, out_features=self.output_shape)

        def forward(self, X):
            """
            Forward pass through neural network.

            Arguments:
                X {torch.tensor} -- Preprocessed input array of shape 
                    (batch_size, input_shape).

            Returns:
                {torch.tensor} -- Predicted value for the given input (batch_size, 1).
        
            """
            if self.act_function == "relu":
                act_function = torch.nn.ReLU()
            elif self.act_function == "sigmoid":
                act_function = torch.nn.Sigmoid()
            elif self.act_function == "tanh":
                act_function = torch.nn.Tanh()

            X = self.input_layer(X.to(self.input_layer.weight.dtype))
            X = act_function(X)

            if self.no_of_layers > 1:
                for layer in self.hidden_layers:
                    X = layer(X)
                    X = act_function(X)

            # For the output layer apply just the linear transformation
            output = self.output_layer(X)

            return output

        
def save_regressor(trained_model):
    """ 
    Utility function to save the trained regressor model in part2_model.pickle.
    """
    # If you alter this, make sure it works in tandem with load_regressor
    with open('part2_model.pickle', 'wb') as target:
        pickle.dump(trained_model, target)
    print("\nSaved model in part2_model.pickle\n")


def load_regressor():
    """ 
    Utility function to load the trained regressor model in part2_model.pickle.
    """
    # If you alter this, make sure it works in tandem with save_regressor
    with open('part2_model.pickle', 'rb') as target:
        trained_model = pickle.load(target)
    print("\nLoaded model in part2_model.pickle\n")
    return trained_model



def RegressorHyperParameterSearch(x_train, y_train):
    """
    Performs a hyper-parameter for fine-tuning the regressor implemented 
    in the Regressor class.

    Arguments:
        Add whatever inputs you need.
        
    Returns:
        The function should return your optimised hyper-parameters. 

    """
    grid = {"no_of_neurons": np.arange(5, 11), 
        "no_of_layers" : np.arange(1, 6),
        "act_function": ["relu", "sigmoid", "tanh"],
        "nb_epoch":[500, 600, 700, 800, 900, 1000],
        "learn_rate":[0.1, 0.01, 0.05]
       }

    classifier = GridSearchCV(Regressor(x=x_train), cv=5, param_grid=grid, scoring="neg_root_mean_squared_error")
    classifier.fit(x_train, y_train)
    print(classifier.best_params_)
    print(classifier.best_score_)
    print(classifier.best_estimator_)
    save_regressor(classifier.best_estimator_)
    return (classifier.best_params_, classifier.best_score_)# Return the chosen hyper parameters


def example_main():

    output_label = "median_house_value"

    data = pd.read_csv("housing.csv")

    # Split input/output
    x_train = data.loc[:, data.columns != output_label]
    y_train = data.loc[:, [output_label]]

    # split data into testing set and training set
    x_train, x_test, y_train, y_test = train_test_split(x_train, y_train, test_size=0.20, random_state=42)

    # Training
    regressor = Regressor(x_train, nb_epoch = 1000, learn_rate = 0.05, no_of_layers = 4, no_of_neurons = 5, act_function = "relu")
    regressor.fit(x_train, y_train)

    # Error
    error = regressor.score(x_test, y_test)
    print("\nRegressor error: {}\n".format(error))


if __name__ == "__main__":
    example_main()
    

