package model;

import java.util.ArrayList;
import java.util.List;

import model.criteria.Criteria;

public class Map {

	private int width;
	private int height;
	private List<Plant> plants;
	private List<Player> players;
	private List<Agent> allAgents;
	private Tile[][] tiles;
	private int time;
	private List<Criteria> criteria;
	private int mode;

	public Map(int mode, int width, int height, List<Player> players, List<Plant> plants, Tile[][] tiles,
			List<Criteria> criteria) {
		setMode(mode);
		setWidth(width);
		setHeight(height);
		setPlayers(players);
		setPlants(plants);
		setTiles(tiles);
		setTime(0);
		setCriteria(criteria);
		for (Plant plant : plants) {
			getTile(plant.getX(), plant.getY()).setPlant(plant);
		}
		List<Agent> allAgents = new ArrayList<Agent>();
		for (Player player : players) {
			for (Agent agent : player.getCurrentAgents()) {
				getTile(agent.getX(), agent.getY()).setAgent(agent);
				allAgents.add(agent);
			}
		}
		setAllAgents(allAgents);
	}

	public int getMode() {
		return mode;
	}

	public void setMode(int mode) {
		this.mode = mode;
	}

	public List<Criteria> getCriteria() {
		return criteria;
	}

	public void setCriteria(List<Criteria> criteria) {
		this.criteria = criteria;
	}

	public int getTime() {
		return time;
	}

	public void setTime(int time) {
		this.time = time;
	}

	public void addAgent(Agent agent) {
		getAllAgents().add(agent);
	}

	public List<Agent> getAllAgents() {
		return allAgents;
	}

	public void setAllAgents(List<Agent> allAgents) {
		this.allAgents = allAgents;
	}

	public int getWidth() {
		return width;
	}

	public void setWidth(int width) {
		this.width = width;
	}

	public int getHeight() {
		return height;
	}

	public void setHeight(int height) {
		this.height = height;
	}

	public Tile[][] getTiles() {
		return tiles;
	}

	public Tile getTile(int x, int y) {
		return getTiles()[x][y];
	}

	public Tile getTile(XY xy) {
		return getTile(xy.getX(), xy.getY());
	}

	public void setTile(Tile tile, int x, int y) {
		getTiles()[x][y] = tile;
	}

	public void setTile(Tile tile, XY xy) {
		setTile(tile, xy.getX(), xy.getY());
	}

	public void setTiles(Tile[][] tiles) {
		this.tiles = tiles;
	}

	public List<Plant> getPlants() {
		return plants;
	}

	public boolean isValid(XY xy) {
		return xy.getX() >= 0 && xy.getX() < getWidth() && xy.getY() >= 0 && xy.getY() < getHeight();
	}

	public void setPlants(List<Plant> plants) {
		this.plants = plants;
	}

	public List<Player> getPlayers() {
		return players;
	}

	public void setPlayers(List<Player> players) {
		this.players = players;
	}

	public List<Plant> findPlants(Tile[][] map) {
		List<Plant> plants = new ArrayList<Plant>();
		for (Tile[] xTiles : map) {
			for (Tile tile : xTiles) {
				if (tile.getPlant() != null) {
					plants.add(tile.getPlant());
				}
			}
		}
		return plants;
	}

	public List<Agent> findAgents(Tile[][] map) {
		List<Agent> agents = new ArrayList<Agent>();
		for (Tile[] xTiles : map) {
			for (Tile tile : xTiles) {
				if (tile.getAgent() != null) {
					agents.add(tile.getAgent());
				}
			}
		}
		return agents;
	}

	public boolean update() throws Exception {
		// Sort by speed and then update the fastest agent
		setTime(getTime() + 1);
		List<Tile> toUpdate = new ArrayList<Tile>();
		for (int i = 0; i < getAllAgents().size() - 1; i++) {
			Agent temp = getAllAgents().get(i);
			if (temp.getSpeed() < getAllAgents().get(i + 1).getSpeed()) {
				getAllAgents().set(i, getAllAgents().get(i + 1));
				getAllAgents().set(i + 1, temp);
			}
			Agent agent = getAllAgents().get(i);
			agent.update(this);
			toUpdate.add(getTile(agent.getX(), agent.getY()));
		}
		
		// Update the slowest agent after everything has finished
		int index = getAllAgents().size() - 1;
		getAllAgents().get(index).update(this);
		toUpdate.add(getTile(getAllAgents().get(index).getX(), getAllAgents().get(index).getY()));
		
		// Update the plants
		for (int i = 0; i < getPlants().size(); i++) {
			Plant plant = getPlants().get(i);
			plant.update(getTiles());
			addPlantHistory(getTiles(), plant.getX(), plant.getX(), toUpdate);
		}

		for (int i = 0; i < toUpdate.size(); i++) {
			Tile tile = toUpdate.get(i);
			tile.addHistory(time);
		}

		for (Criteria criteria : getCriteria()) {
			if (criteria.isFinished(this)) {
				System.out.println(criteria.toString());
				return true;
			}
		}
		return false;
	}

	public void addPlantHistory(Tile[][] tiles, int x, int y, List<Tile> toUpdate) {

		if (isValid(tiles, x, y) && !toUpdate.contains(tiles[x][y])) {
			toUpdate.add(tiles[x][y]);
		}
		if (isValid(tiles, x + 1, y) && !toUpdate.contains(tiles[x + 1][y])) {
			toUpdate.add(tiles[x + 1][y]);
		}
		if (isValid(tiles, x - 1, y) && !toUpdate.contains(tiles[x - 1][y])) {
			toUpdate.add(tiles[x - 1][y]);
		}
		if (isValid(tiles, x, y + 1) && !toUpdate.contains(tiles[x][y + 1])) {
			toUpdate.add(tiles[x][y + 1]);
		}
		if (isValid(tiles, x, y - 1) && !toUpdate.contains(tiles[x][y - 1])) {
			toUpdate.add(tiles[x][y - 1]);
		}
	}

	public boolean isValid(Tile[][] tiles, int x, int y) {
		if (x >= 0 && x < tiles.length) {
			if (y >= 0 && y < tiles[x].length) {
				return true;
			}
		}
		return false;
	}

	public String toString() {
		String output = "\nWidth=" + getWidth() + "\tHeight=" + getHeight() + "\tMode=" + getMode();
		output += "\nPlayers=" + getPlayers().size() + "\tPlants=" + getPlants().size();
		for (int y = 0; y < getHeight(); y++) {
			output += "\n";
			for (int x = 0; x < getWidth(); x++) {
				output += getTile(x, y).toString() + "\t";
			}
		}
		output += printPlants();
		output += printPlayers();
		output += printCriteria();

		return output;
	}

	public String printFood() {
		String output = "Food";
		for (int y = 0; y < getHeight(); y++) {
			output += "\n";
			for (int x = 0; x < getWidth(); x++) {
				output += getTile(x, y).getFood() + "\t";
			}
		}
		return output;
	}

	public String printDirt() {
		String output = "Dirt";
		for (int y = 0; y < getHeight(); y++) {
			output += "\n";
			for (int x = 0; x < getWidth(); x++) {
				output += getTile(x, y).getDirt() + "\t";
			}
		}
		return output;
	}

	public String printPlayers() {
		String output = "\nPlayers:";
		for (Player player : getPlayers()) {
			output += "\n" + player.toString();
		}
		return output;
	}

	public String printAgents() {
		String output = "\nAgents:";
		for (Agent agent : getAllAgents()) {
			output += "\n" + agent.toString();
		}
		/*
		 * for (Player player : getPlayers()) { for (Agent agent :
		 * player.getAgents()) {
		 * 
		 * } }
		 */
		return output;
	}

	public String printPlants() {
		String output = "\nPlants:";
		for (Plant plant : getPlants()) {
			output += "\n\t" + plant.toString();
		}
		return output;
	}

	public String printCriteria() {
		String output = "\nCriteria:";
		for (Criteria criteria : getCriteria()) {
			output += "\n\t" + criteria.toString();
		}
		return output;
	}

}
