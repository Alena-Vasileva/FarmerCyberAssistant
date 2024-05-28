# -*- coding: utf-8 -*-
from time import time
from weather import Location, WeatherAPI
from weather_forecaster import WeatherForecaster
from account_utils import AccountUtils


class RecommendationMaker:    # TODO: Test

    RECOMMENDATION_TYPES = ['Watering', 'Fertilizing', 'Harvest']
    # 86 400 seconds = 1 day
    relevance_periods = {'Watering': 50_000, 'Fertilizing': 100_000, 'Harvest': 500_000}

    @staticmethod
    def get_all_recommendations(fields):
        recommendations = []
        locations = []
        for field in fields:
            if not AccountUtils.field_is_correct(field, contains_all_keys=True) \
                    or field['PlantName'] in [None, 'None']:
                locations.append(None)
                recommendations.append([])
            else:
                location = Location(field['Latitude'], field['Longitude'])
                locations.append(location)
                weather_list = WeatherAPI.get_all_simple_predictions(location)
                weather = WeatherForecaster.get_forecast(weather_list)
                recommendations.append(RecommendationMaker.__get_caching_recommendations(field, weather))
        return recommendations

    @staticmethod
    def __get_caching_recommendations(target_field, weather):
        # get from cache
        ok, ret = RecommendationCacher.get((target_field, weather))
        if ok:
            return ret

        recommendations = RecommendationMaker.__get_recommendations(target_field, weather)
        # save to cache
        RecommendationCacher.set((target_field, weather), recommendations)

        return recommendations

    @staticmethod
    def __get_recommendations(target_field, weather):
        recommendations = []
        plant = target_field['PlantName']
        planting_date = target_field['PlantingDate']    # unix timestamp
        temperature = weather.temperature
        humidity = weather.humidity

        minimal_harvest_days = {'Carrot': 80,
                                'Corn': 90,
                                'Potato': 70,
                                'Tomato': 80,
                                'Wheat': 85}
        maximum_harvest_days = {'Carrot': 115,
                                'Corn': 150,
                                'Potato': 120,
                                'Tomato': 120,
                                'Wheat': 115}
        if time() - planting_date > minimal_harvest_days[plant] * 86400:    # Harvest
            recommendation_type = 'Harvest'
            recommendation_value = f'Нужно собрать урожай в течение {minimal_harvest_days[plant]}-' \
                f'{maximum_harvest_days[plant]} дней после посадки.'
            relevance_limit_timestamp = round(time()) + RecommendationMaker.relevance_periods[recommendation_type]
            recommendations.append(Recommendation(recommendation_type, recommendation_value, relevance_limit_timestamp))

        watering_rates = {'Carrot': 0.6,
                          'Corn': 0.2,
                          'Potato': 0.1,
                          'Tomato': 1,
                          'Wheat': 0}
        watering_needs = watering_rates[plant] * (1 + 0.1 * max(temperature - 20, 0)) - 0.005 * humidity
        if watering_needs > 0.2:    # Watering
            recommendation_type = 'Watering'
            if 0.2 < watering_needs <= 0.5:
                recommendation_value = 'Полейте немного.'
            elif 0.5 < watering_needs <= 1:
                recommendation_value = 'Полейте средне.'
            elif 1 < watering_needs < 2:
                recommendation_value = 'Полейте сильно.'
            else:    # 2 < watering_needs
                recommendation_value = 'Полейте очень сильно.'
            relevance_limit_timestamp = round(time()) + RecommendationMaker.relevance_periods[recommendation_type]
            recommendations.append(Recommendation(recommendation_type, recommendation_value, relevance_limit_timestamp))

        active_fertilizing_periods = {'Carrot': 20,
                                      'Corn': 40,
                                      'Potato': 30,
                                      'Tomato': 20,
                                      'Wheat': 7}
        if time() - planting_date < active_fertilizing_periods[plant] * 86400 and humidity > 30:    # Fertilizing
            recommendation_type = 'Fertilizing'
            recommendation_value = 'Нужно много удобрений.'
            relevance_limit_timestamp = round(time()) + RecommendationMaker.relevance_periods[recommendation_type]
            recommendations.append(Recommendation(recommendation_type, recommendation_value, relevance_limit_timestamp))
        elif time() - planting_date < (maximum_harvest_days[plant] - 5) * 86400 and humidity > 60:
            recommendation_type = 'Fertilizing'
            recommendation_value = 'Нужно немного удобрений.'
            relevance_limit_timestamp = round(time()) + RecommendationMaker.relevance_periods[recommendation_type]
            recommendations.append(Recommendation(recommendation_type, recommendation_value, relevance_limit_timestamp))

        return recommendations


class Recommendation:

    def __init__(self, recommendation_type_name: str, value: str, relevance_limit_timestamp: int):
        self.TypeName = recommendation_type_name
        self.Value = value
        self.RelevanceLimitTimestamp = relevance_limit_timestamp

    def get_object_dict(self):
        return self.__dict__


class RecommendationCacher:
    __recommendation_cache = []
    __cache_ttl = 10_000
    __max_cache_size = 1_000

    @staticmethod
    def get(key):
        RecommendationCacher.invalidate()

        for item in RecommendationCacher.__recommendation_cache:
            if item.key == key:
                return True, item.value

        return False, None

    @staticmethod
    def set(key, value):
        RecommendationCacher.__recommendation_cache.append(RecommendationCacher.CachedItem(key, value))

        RecommendationCacher.invalidate()

    @staticmethod
    def invalidate():
        new_cache = []
        for item in RecommendationCacher.__recommendation_cache:
            if item.cached_time + RecommendationCacher.__cache_ttl > time():
                new_cache.append(item)

        # сортируем от самого свежего, к менее свежему
        new_cache.sort(key=lambda x: x.cached_time, reverse=True)

        new_cache = new_cache[:min(len(new_cache), RecommendationCacher.__max_cache_size)]

        RecommendationCacher.__recommendation_cache = new_cache

    class CachedItem:
        def __init__(self, key, value):
            self.key = key
            self.value = value
            self.cached_time = time()
