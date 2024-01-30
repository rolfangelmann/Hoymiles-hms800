"""Support for Hoymiles number sensors."""
from dataclasses import dataclass
from enum import Enum
import logging

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, HASS_CONFIG_COORDINATOR
from .entity import HoymilesCoordinatorEntity


class SetAction(Enum):
    """Enum for set actions."""

    POWER_LIMIT = 1

@dataclass(frozen=True)
class HoymilesNumberSensorEntityDescriptionMixin:
    """Mixin for required keys."""

@dataclass(frozen=True)
class HoymilesNumberSensorEntityDescription(NumberEntityDescription):
    """Describes Hoymiles number sensor entity."""

    set_action: SetAction = None
    conversion_factor: float = None


CONFIG_CONTROL_ENTITIES = (
    HoymilesNumberSensorEntityDescription(
        key = "limit_power_mypower",
        translation_key="limit_power_mypower",
        mode =  NumberMode.SLIDER,
        device_class = NumberDeviceClass.POWER_FACTOR,
        set_action = SetAction.POWER_LIMIT,
        conversion_factor = 0.1,
    ),
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Hoymiles number entities."""
    hass_data = hass.data[DOMAIN][entry.entry_id]
    config_coordinator = hass_data[HASS_CONFIG_COORDINATOR]

    sensors = []
    for description in CONFIG_CONTROL_ENTITIES:
        sensors.append(HoymilesNumberEntity(entry, description, config_coordinator))

    async_add_entities(sensors)


class HoymilesNumberEntity(HoymilesCoordinatorEntity, NumberEntity):
    """Hoymiles Number entity."""

    def __init__(self, config_entry: ConfigEntry, description: HoymilesNumberSensorEntityDescription, coordinator: HoymilesCoordinatorEntity,) -> None:
        """Initialize the HoymilesNumberEntity."""
        super().__init__(config_entry, description, coordinator)
        self._attribute_name = description.key
        self._conversion_factor = description.conversion_factor
        self._set_action = description.set_action
        self._native_value = None
        self._assumed_state = False

        self.update_state_value()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.update_state_value()
        super()._handle_coordinator_update()


    @property
    def native_value(self) -> float:
        """Get the native value of the entity."""
        return self._native_value

    @property
    def assumed_state(self):
        """Return the assumed state of the entity."""
        return self._assumed_state

    def set_native_value(self, value: float) -> None:
        """Set the native value of the entity.

        Args:
            value (float): The value to set.
        """
        if self._set_action == SetAction.POWER_LIMIT:
                inverter = self.coordinator.get_inverter()
                if(value < 0 and value > 100):
                    _LOGGER.error("Power limit value out of range")
                    return
                inverter.set_power_limit(value)
        else:
            _LOGGER.error("Invalid set action!")
            return

        self._assumed_state = True
        self._native_value = value


    def update_state_value(self):
        """Update the state value of the entity."""
        self._native_value =  getattr(self.coordinator.data, self._attribute_name, None)

        self._assumed_state = False

        if self._native_value is not None and self._conversion_factor is not None:
            self._native_value *= self._conversion_factor
