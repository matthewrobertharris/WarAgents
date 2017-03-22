package readers;

import java.util.List;

import model.Plant;

public interface PlantReader {
	public Plant convertPlant(String plantData);

	public List<Plant> convertPlants(String gameData);
}
