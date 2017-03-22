package generators;

import model.Plant;

public class DefaultPlantGenerator implements PlantGenerator {
	
	public static final int RATE = 8;

	public Plant generatePlant(int x, int y) {
		return new Plant(x, y, RATE);
	}
}
