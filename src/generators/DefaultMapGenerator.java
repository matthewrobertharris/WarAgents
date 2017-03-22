package generators;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

import model.Agent;
import model.Map;
import model.Plant;
import model.Player;
import model.Tile;
import model.criteria.Criteria;
import model.criteria.SurviveTurns;
import model.tree.Node;
import model.tree.Tree;

public class DefaultMapGenerator implements MapGenerator {

	public static final int DIRT = 1;
	public static final int FOOD = 10;
	public static final int WIDTH = 10;
	public static final int HEIGHT = 10;
	public static final int TEAMS = 1;
	public static final int PLANTS = 0;

	private PlayerGenerator playerGen;
	private NodeGenerator nodeGen;
	private AgentGenerator agentGen;
	private PlantGenerator plantGen;
	
	public DefaultMapGenerator(PlayerGenerator playerGen, NodeGenerator nodeGen,
			AgentGenerator agentGen, PlantGenerator plantGen) {
		setPlayerGen(playerGen);
		setNodeGen(nodeGen);
		setAgentGen(agentGen);
		setPlantGen(plantGen);
	}

	public PlayerGenerator getPlayerGen() {
		return playerGen;
	}

	public void setPlayerGen(PlayerGenerator playerGen) {
		this.playerGen = playerGen;
	}

	public NodeGenerator getNodeGen() {
		return nodeGen;
	}

	public void setNodeGen(NodeGenerator nodeGen) {
		this.nodeGen = nodeGen;
	}

	public AgentGenerator getAgentGen() {
		return agentGen;
	}

	public void setAgentGen(AgentGenerator agentGen) {
		this.agentGen = agentGen;
	}

	public PlantGenerator getPlantGen() {
		return plantGen;
	}

	public void setPlantGen(PlantGenerator plantGen) {
		this.plantGen = plantGen;
	}

	@Override
	public Map generateMap(int width, int height, int teams, int numberPlants) {
		Tile[][] tiles = new Tile[width][height];
		for (int x = 0; x < width; x++) {
			for (int y = 0; y < height; y++) {
				tiles[x][y] = new Tile(DIRT, FOOD, null, null);
			}
		}
		int[] locations = generateLocations(width, height, teams, numberPlants);
		List<Player> players = new ArrayList<Player>();
		for (int i = 0; i < teams; i++) {
			//int[] xy = convertPos(width, height, locations[i]);
			int[] xy = new int[] {0,0};
			List<Agent> agents = new ArrayList<Agent>();
			Node node = getNodeGen().generateNode();
			Tree tree = new Tree("Default", node);
			List<Tree> trees = new ArrayList<Tree>();
			trees.add(tree);
			Player player = getPlayerGen().generatePlayer(trees);
			Agent agent = getAgentGen().createAgent(player, xy[0], xy[1]);
			agents.add(agent);
			player.addAgent(agent);
			tiles[xy[0]][xy[1]].setAgent(agent);
			players.add(player);
			
		}
		List<Plant> plants = new ArrayList<Plant>();
		for (int i = teams; i < teams + numberPlants; i++) {
			int[] xy = convertPos(width, height, locations[i]);
			Plant plant = getPlantGen().generatePlant(xy[0], xy[1]);
			tiles[xy[0]][xy[1]].setPlant(plant);
		}
		
		Criteria criteria = new SurviveTurns(5);
		List<Criteria> criteriaList = new ArrayList<Criteria>();
		criteriaList.add(criteria);
		int mode = 1; //1=CLICK, 2=CONST, 3=FIXED
		return new Map(mode, width, height, players, plants, tiles, criteriaList);
	}

	@Override
	public int[] generateLocations(int width, int height, int teams, int plants) {
		int totalTiles = width * height;
		int totalLocs = teams + plants;
		if (totalLocs > totalTiles) {
			return null; // Not possible to do this.
		} else {
			return generateMN(totalLocs, totalTiles);
		}
	}

	private int[] generateMN(int M, int N) {
		Random rnd = new Random();
		int[] locations = new int[M];
		List<Integer> positions = new ArrayList<Integer>();
		for (int i = 0; i < N; i++) {
			positions.add(i);
		}
		for (int i = 0; i < M; i++) {
			int pos = rnd.nextInt(positions.size());
			locations[i] = positions.get(pos);
			positions.remove(pos);
		}
		return locations;
	}

	private int[] convertPos(int width, int height, int position) {
		int y = position / width;
		int x = Math.floorMod(position, height);
		System.out.println("W=" + width + " H=" + height + "P=" + position);
		System.out.println("X=" + x + " Y=" + y);
		return new int[] { x, y };
	}

	public String toString() {
		String output = "DefaultMapGenerator";
		output += " DIRT=" + DIRT;
		output += " FOOD=" + FOOD;
		return output;
	}

	@Override
	public Map generateMap() {
		return generateMap(WIDTH, HEIGHT, TEAMS, PLANTS);
	}
}
