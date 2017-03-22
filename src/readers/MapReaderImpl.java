package readers;

import java.util.ArrayList;
import java.util.List;

import model.Agent;
import model.Map;
import model.Plant;
import model.Player;
import model.Thing;
import model.Tile;
import model.criteria.Criteria;

public class MapReaderImpl implements MapReader {
	private PlantReader plantReader;
	private PlayerReader playerReader;
	private CriteriaReader criteriaReader;
	private ModeReader modeReader;

	public MapReaderImpl(PlantReader plantReader, PlayerReader playerReader, CriteriaReader criteriaReader,
			ModeReader modeReader) {
		setPlantReader(plantReader);
		setPlayerReader(playerReader);
		setCriteriaReader(criteriaReader);
		setModeReader(modeReader);
	}

	public ModeReader getModeReader() {
		return modeReader;
	}

	public void setModeReader(ModeReader modeReader) {
		this.modeReader = modeReader;
	}

	public CriteriaReader getCriteriaReader() {
		return criteriaReader;
	}

	public void setCriteriaReader(CriteriaReader criteriaReader) {
		this.criteriaReader = criteriaReader;
	}

	public PlantReader getPlantReader() {
		return plantReader;
	}

	public void setPlantReader(PlantReader plantReader) {
		this.plantReader = plantReader;
	}

	public PlayerReader getPlayerReader() {
		return playerReader;
	}

	public void setPlayerReader(PlayerReader playerReader) {
		this.playerReader = playerReader;
	}

	@Override
	public Tile[][] convertTiles(String gameData) {
		String[] lines = gameData.split(System.lineSeparator());
		int height = Integer.valueOf(lines[0].split("=")[1]);
		int width = Integer.valueOf(lines[1].split("=")[1]);
		int[][] food = new int[width][height];
		for (int i = 3; i < 3 + height; i++) {
			int y = i - 3;
			String[] line = lines[i].split(" ");
			for (int x = 0; x < width; x++) {
				food[x][y] = Integer.valueOf(line[x]);
			}
		}
		int[][] dirt = new int[width][height];
		for (int i = 4 + height; i < (2 * height + 4); i++) {
			int y = i - (4 + height);
			String[] line = lines[i].split(" ");
			for (int x = 0; x < width; x++) {
				dirt[x][y] = Integer.valueOf(line[x]);
			}
		}

		Tile[][] tiles = new Tile[width][height];
		for (int x = 0; x < width; x++) {
			for (int y = 0; y < height; y++) {
				Tile tile = new Tile(dirt[x][y], food[x][y], null, null);
				tiles[x][y] = tile;
			}
		}
		return tiles;
	}

	@Override
	public Map convertMap(String gameData) {
		String[] lines = gameData.split(System.lineSeparator());
		int height = Integer.valueOf(lines[0].split("=")[1]);
		int width = Integer.valueOf(lines[1].split("=")[1]);
		List<Plant> plants = getPlantReader().convertPlants(gameData);
		Tile[][] tiles = convertTiles(gameData);
		List<Player> players = getPlayerReader().convertPlayers(gameData);
		List<Thing> things = aggregateThings(players, plants);
		List<Criteria> criteria = getCriteriaReader().readCriteriaList(things, players, gameData);
		int mode = getModeReader().readMode(players, gameData);
		Map map = new Map(mode, width, height, players, plants, tiles, criteria);
		return map;
	}
	
	private List<Thing> aggregateThings(List<Player> players, List<Plant> plants) {
		List<Thing> things = new ArrayList<Thing>();
		for(Player player : players) {
			for(Agent agent : player.getAllAgents()) {
				things.add(agent);
			}
		}
		for(Plant plant : plants) {
			things.add(plant);
		}
		return things;
	}

}
