package readers;

import model.Map;
import model.Tile;

public interface MapReader {

	public Tile[][] convertTiles(String mapData);
	public Map convertMap(String gameData);
}
