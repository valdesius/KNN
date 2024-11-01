import tensorflow as tf
from tensorflow.keras.applications.vgg16 import VGG16
from tensorflow.keras.preprocessing import image
from tensorflow.keras.models import Model
from tensorflow.keras.layers import GlobalAveragePooling2D, Flatten, Rescaling, Concatenate
from sklearn.neighbors import KNeighborsClassifier
from sklearn.decomposition import PCA
from sklearn.metrics import accuracy_score, classification_report
import numpy as np

!pip install split_folders

!gdown --id 1ukT3Ey5X0eUeidhAMo4gi0Qy11aME5E2

!unzip dataset.zip

import splitfolders

input_folder = "/content/cat_v1" #Enter Input Folder
output = "/content/ready_dataset" #Enter Output Folder


splitfolders.ratio(input_folder, output=output, seed=42, ratio=(0.9, 0.0, 0.1))

batch_size = 32
img_height = 224
img_width = 224

train_ds = tf.keras.utils.image_dataset_from_directory(
  directory='ready_dataset/train', # путь к папке с обучающими данными
  label_mode = 'int',       # представление правильных ответов картинок в виде чисел (Label Encoding): 0, 1, 2, 3... (Также можно использовать One-Hot Encoding, для этого напишите categorical) (Если у вас задача бинарной классификации пишите binary)
  color_mode='rgb',         # представление каждой картинки в RGB формате
  batch_size=batch_size,    # параметр, с помощью которого можно регулировать порцию подаваемых примеров (картинок) для сети за одну итерацию обучения
  seed=123,
  image_size=(img_height, img_width), # нейронная сеть всегда принимает изображение определённого размера. Поэтому необходимо предварительно поменять размер каждого изображения
  shuffle=True)                       # перетасовка данных, чтобы генерировать данные не в определённом порядке (сначала 1 класс, потом 2 класс), а случайным образом

test_ds = tf.keras.utils.image_dataset_from_directory(
  directory='ready_dataset/test',  # путь к папке с тестовыми данными
  label_mode = 'int',
  color_mode='rgb',
  batch_size=batch_size,
  seed=123,
  image_size=(img_height, img_width),
  shuffle=False)

# Добавьте в наши созданные наборы данных функцию нормализации. Она перед подачей изображений на вход сети будет автоматически нормализовывать изображения по минимаксной нормализации.
# По сути наши сформированные наборы данных автоматически формирует пару: x (признаки) и y (целевые метки)
normalization_layer = Rescaling(1./255)
normalized_ds = train_ds.map(lambda x, y: (normalization_layer(x), y))
normalized_ds = test_ds.map(lambda x, y: (normalization_layer(x), y))

# здесь вы можете найти документацию по данному генератору: https://www.tensorflow.org/api_docs/python/tf/keras/utils/image_dataset_from_directory

# Визуализация ваших данных

import matplotlib.pyplot as plt

class_names = train_ds.class_names # список классов

plt.figure(figsize=(10, 10))
for images, labels in train_ds.take(1):
  for i in range(9):
    ax = plt.subplot(3, 3, i + 1)
    plt.imshow(images[i].numpy().astype("uint8"))
    plt.title(class_names[labels[i]])
    plt.axis("off")

# Функция формирования набора данных (картинки и метки)
def extract_dataset_images(dataset):
  labels = []
  images = []
  for batch, batch_labels in dataset:
    images.append(batch.numpy().reshape((batch.shape[0], -1))) # Делаем картинки в виде векторов
    labels.append(batch_labels.numpy())
  return np.concatenate(images), np.concatenate(labels)

x_train, y_train = extract_dataset_images(train_ds)

def train_and_test_KNN(x_train, y_train):
  # Обучение KNN на картинках (количество соседей n_neighbors, метрику расстояний и функцию взвешивания нужно подобрать)
  knn_classifier = KNeighborsClassifier(n_neighbors=5, metric='manhattan', weights='distance')
  knn_classifier.fit(x_train, y_train)

  # Тестирование

  # Извлекаем тестовые картинки и соответствующие метки
  x_test, y_test = extract_dataset_images(test_ds)
  # Классификация тестовых изображений с использованием KNN
  y_pred = knn_classifier.predict(x_test)

  report = classification_report(y_test, y_pred, target_names=class_names)
  print("KNN on test data:")
  print(report)

train_and_test_KNN(x_train, y_train)

x_train, y_train = extract_dataset_images(train_ds)

def train_and_test_PCA_KNN(x_train, y_train):
  # Применение PCA для извлечения только полезной информации и уменьшения размерности признаков (количество компонент нужно подобрать)
  pca = PCA(n_components=60)
  x_train_pca = pca.fit_transform(x_train)

  # Обучение KNN на сжатых признаках PCA (количество соседей n_neighbors, метрику расстояний и функцию взвешивания нужно подобрать)
  knn_classifier = KNeighborsClassifier(n_neighbors=5, metric='minkowski', weights='distance')
  knn_classifier.fit(x_train_pca, y_train)

  # Тестирование

  # Извлекаем тестовые картинки и соответствующие метки
  x_test, y_test = extract_dataset_images(test_ds)

  # Применение созданного ранее PCA для тестовых данных
  x_test_pca = pca.transform(x_test)

  # Классификация тестовых изображений с использованием KNN
  y_pred = knn_classifier.predict(x_test_pca)

  report = classification_report(y_test, y_pred, target_names=class_names)
  print("PCA + KNN on test data:")
  print(report)

train_and_test_PCA_KNN(x_train, y_train)

from tensorflow.keras.applications import EfficientNetB7
from tensorflow.keras.layers import GlobalAveragePooling2D, Flatten
from tensorflow.keras.models import Model
import numpy as np

# Создание предварительно обученной модели EfficientNetB7 для извлечения признаков со слоя block7b_add
def createPreTrainedModel(input_shape):
    # Загрузка предварительно обученной модели EfficientNetB7 без последнего полносвязанного слоя
    base_model = EfficientNetB7(weights='imagenet', include_top=False, input_shape=input_shape)

    # Выбор последнего слоя максимального пулинга для извлечения высокоуровневых признаков
    max_pooling_layer = base_model.get_layer('block7b_add').output

    # Применение Global Average Pooling (для усреднения признаков и таким образом уменьшения размерности признаков)
    global_avg_pooling_layer = GlobalAveragePooling2D()(max_pooling_layer)

    # Создание новой модели
    model = Model(inputs=base_model.input, outputs=global_avg_pooling_layer)
    return model

# Вариант без GlobalAveragePooling2D
def createPreTrainedModelWithoutGAP(input_shape):
    # Загрузка предварительно обученной модели EfficientNetB7 без последнего полносвязанного слоя
    base_model = EfficientNetB7(weights='imagenet', include_top=False, input_shape=input_shape)

    # Выбор последнего слоя максимального пулинга для извлечения высокоуровневых признаков
    max_pooling_layer = base_model.get_layer('block7b_add').output

    # Применение Flatten (чтобы выводить вектор признаков, поскольку KNN работает с векторами)
    flatten_layer = Flatten()(max_pooling_layer)

    # Создание новой модели
    model = Model(inputs=base_model.input, outputs=flatten_layer)
    return model

# Функция формирования набора данных (извлечённые из предобученной CNN признаки и метки)
# Мы делаем predict для каждого батча нашего набора данных и получаем на выходе признаки из слоя block7b_add.
# Мы сохраняем признаки изображений и их соответствующие метки классов.
def extract_features(dataset, model):
    features = []
    labels = []
    for batch_images, batch_labels in dataset:
        batch_features = model.predict(batch_images)
        labels.append(batch_labels.numpy())
        features.append(batch_features)
    return np.concatenate(features), np.concatenate(labels)

# Создаём модель и извлекаем признаки из изображений обучающей выборки train_ds и формируем обучающую выборку.
model = createPreTrainedModel((224, 224, 3))
x_train_features, y_train_labels = extract_features(train_ds, model)

def train_and_test_CNN_PCA_KNN(x_train_features, y_train_labels):
  # Применение PCA для извлечения только полезной информации и уменьшения размерности признаков (количество компонент нужно подобрать)
  pca = PCA(n_components=40)
  x_train_pca = pca.fit_transform(x_train_features)

  # Обучение KNN на уменьшенных признаках (количество соседей n_neighbors, метрику расстояний и функцию взвешивания нужно подобрать)
  # Список метрик: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.distance_metrics.html#sklearn.metrics.pairwise.distance_metrics
  knn_classifier = KNeighborsClassifier(n_neighbors=4, metric='manhattan', weights='distance')
  knn_classifier.fit(x_train_pca, y_train_labels)

  # Тестирование

  # Извлекаем признаки из изображений тестовой выборки test_ds
  x_test_features, y_test_labels = extract_features(test_ds, model)

  # Применение созданного ранее PCA для тестовых данных
  x_test_pca = pca.transform(x_test_features)

  # Классификация тестовых изображений с использованием KNN
  y_pred = knn_classifier.predict(x_test_pca)

  # Рассчёт точности
  report = classification_report(y_test_labels, y_pred, target_names=class_names)
  print("CNN + PCA + KNN accuracy:")
  print(report)

train_and_test_CNN_PCA_KNN(x_train_features, y_train_labels)

import matplotlib.pyplot as plt

def plot_data_CNN_PCA_KNN(x_train_features, y_train_labels):
    # Применение PCA для извлечения только полезной информации и уменьшения размерности признаков
    pca = PCA(n_components=3)
    x_train_pca = pca.fit_transform(x_train_features)

    # Уникальные метки классов
    unique_labels = set(y_train_labels)

    # Создание цветовой карты
    colors = plt.cm.get_cmap('hsv', len(unique_labels))

    fig = plt.figure(figsize=(12, 12))
    ax = fig.add_subplot(projection='3d')
    # Построение графика
    for i, label in enumerate(unique_labels):
        # Индексы для текущего класса
        indices = [j for j, y in enumerate(y_train_labels) if y == label]
        ax.scatter(x_train_pca[indices, 0], x_train_pca[indices, 1], x_train_pca[indices, 2],
                    color=colors(i), label=class_names[i], alpha=0.75)
    ax.view_init(-140, 60)
    plt.title('PCA of Training Data')
    plt.xlabel('Principal Component 1')
    plt.ylabel('Principal Component 2')
    plt.legend()
    plt.grid()
    plt.show()

plot_data_CNN_PCA_KNN(x_train_features, y_train_labels)

"""это 1 модель

> EfficientNetB7



"""

# Создание предварительно обученной модели VGG-16 для извлечения признаков со слоя block5_pool
# Список предобученных моделей: https://keras.io/api/applications/
# Не забудьте подключить GPU.
def createPreTrainedModel(input_shape):
  # Загрузка предварительно обученной модели VGG-16 без последнего полносвязанного слоя
  base_model = VGG16(weights='imagenet', include_top=False, input_shape=input_shape)

  # Выбор последнего слоя максимального пулинга для извлечения высокоуровневых признаков
  max_pooling_layer = base_model.get_layer('block5_pool').output

  # Применение Global Average Pooling (для усреднения признаков и таким образом уменьшения размерности признаков)
  global_avg_pooling_layer = GlobalAveragePooling2D()(max_pooling_layer)

  # Создание новой модели
  model = Model(inputs=base_model.input, outputs=global_avg_pooling_layer)
  return model

# # Вариант без GlobalAveragePooling2D
# def createPreTrainedModel(input_shape):
#   # Загрузка предварительно обученной модели VGG-16 без последнего полносвязанного слоя
#   base_model = VGG16(weights='imagenet', include_top=False, input_shape=input_shape)

#   # Выбор последнего слоя максимального пулинга для извлечения высокоуровневых признаков
#   max_pooling_layer = base_model.get_layer('block5_pool').output

#   # Применение Flatten (чтобы выводить вектор признаков, поскольку KNN работает с векторами)
#   flatten_layer = Flatten()(max_pooling_layer)

#   # Создание новой модели
#   model = Model(inputs=base_model.input, outputs=flatten_layer)
#   return model


# # Функция формирования набора данных (извлечённые из предобученной CNN признаки и метки)
# Мы делаем predict для каждого батча нашего набора данных и получаем на выходе признаки из слоя block5_pool.
# Мы сохраняем признаки изображений и их соответствующие метки классов.
def extract_features(dataset, model):
    features = []
    labels = []
    for batch_images, batch_labels in dataset:
        batch_features = model.predict(batch_images)
        labels.append(batch_labels.numpy())
        features.append(batch_features)
    return np.concatenate(features), np.concatenate(labels)

# Создаём модель и извлекаем признаки из изображений обучающей выборки train_ds и формируем обучающую выборку.
model = createPreTrainedModel((224, 224, 3))
x_train_features, y_train_labels = extract_features(train_ds, model)

def train_and_test_CNN_PCA_KNN(x_train_features, y_train_labels):
  # Применение PCA для извлечения только полезной информации и уменьшения размерности признаков (количество компонент нужно подобрать)
  pca = PCA(n_components=250)
  x_train_pca = pca.fit_transform(x_train_features)

  # Обучение KNN на уменьшенных признаках (количество соседей n_neighbors, метрику расстояний и функцию взвешивания нужно подобрать)
  # Список метрик: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.distance_metrics.html#sklearn.metrics.pairwise.distance_metrics
  knn_classifier = KNeighborsClassifier(n_neighbors=5, metric='minkowski', weights='distance')
  knn_classifier.fit(x_train_pca, y_train_labels)

  # Тестирование

  # Извлекаем признаки из изображений тестовой выборки test_ds
  x_test_features, y_test_labels = extract_features(test_ds, model)

  # Применение созданного ранее PCA для тестовых данных
  x_test_pca = pca.transform(x_test_features)

  # Классификация тестовых изображений с использованием KNN
  y_pred = knn_classifier.predict(x_test_pca)

  # Рассчёт точности
  report = classification_report(y_test_labels, y_pred, target_names=class_names)
  print("CNN + PCA + KNN accuracy:")
  print(report)

train_and_test_CNN_PCA_KNN(x_train_features, y_train_labels)

import matplotlib.pyplot as plt

def plot_data_CNN_PCA_KNN(x_train_features, y_train_labels):
    # Применение PCA для извлечения только полезной информации и уменьшения размерности признаков
    pca = PCA(n_components=3)
    x_train_pca = pca.fit_transform(x_train_features)

    # Уникальные метки классов
    unique_labels = set(y_train_labels)

    # Создание цветовой карты
    colors = plt.cm.get_cmap('hsv', len(unique_labels))

    fig = plt.figure(figsize=(12, 12))
    ax = fig.add_subplot(projection='3d')
    # Построение графика
    for i, label in enumerate(unique_labels):
        # Индексы для текущего класса
        indices = [j for j, y in enumerate(y_train_labels) if y == label]
        ax.scatter(x_train_pca[indices, 0], x_train_pca[indices, 1], x_train_pca[indices, 2],
                    color=colors(i), label=class_names[i], alpha=0.75)
    ax.view_init(-140, 60)
    plt.title('PCA of Training Data')
    plt.xlabel('Principal Component 1')
    plt.ylabel('Principal Component 2')
    plt.legend()
    plt.grid()
    plt.show()

plot_data_CNN_PCA_KNN(x_train_features, y_train_labels)

"""VGG-16 модель

"""
