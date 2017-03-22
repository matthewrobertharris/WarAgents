package readers;

import java.util.ArrayList;
import java.util.List;

import model.Plant;

public class PlantReaderImpl implements PlantReader {

	@Override
	public Plant convertPlant(String plantData) {
		String[] values = plantData.split(",");
		int x = Integer.valueOf(values[0].split("=")[1]);
		int y = Integer.valueOf(values[1].split("=")[1]);
		int rate = Integer.valueOf(values[2].split("=")[1]);
		Plant plant = new Plant(x, y, rate);
		return plant;
	}

	@Override
	public List<Plant> convertPlants(String gameData) {
		String[] lines = gameData.split(System.lineSeparator());
		int height = Integer.valueOf(lines[0].split("=")[1]);
		int plantLine = 4 + (height * 2);
		int plantNumber = Integer.valueOf(lines[plantLine].split("=")[1]);
		List<Plant> plants = new ArrayList<Plant>();
		for (int i = 1; i <= plantNumber; i++) {
			Plant plant = convertPlant(lines[plantLine + i]);
			plants.add(plant);
		}
		return plants;
	}

}
