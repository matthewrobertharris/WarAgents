package generators;

import model.Map;

public interface MapGenerator {

	public Map generateMap();
	public Map generateMap(int width, int height, int teams, int plants);
	public int[] generateLocations(int width, int height, int teams, int plants);
	public String toString();
}
