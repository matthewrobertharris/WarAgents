package main;

import java.util.List;

import model.Agent;
import model.AgentHistory;
import model.Map;
import model.Player;
import model.Tile;
import model.TileHistory;

public class ProcessHistory {

	public static String processHistory(Map map, List<Player> players) {
		String output = "Player History\n";
		for (Player player : players) {
			output += processPlayerHistory(player);
		}
		output += processMapHistory(map);
		return output;
	}

	public static String processPlayerHistory(Player player) {
		String output = "";
		for (Agent agent : player.getAllAgents()) {
			output += processAgentHistory(agent);
		}
		return output;
	}
	
	public static String processAgentHistory(Agent agent) {
		String output = agent.getID() + " history\n";
		output += "Born=" + agent.getBirth() + " Death=" + agent.getDeath() + "\n";
		for (AgentHistory history : agent.getHistory()) {
			output += history.toString() + "\n";
		}
		return output;
	}

	public static String processMapHistory(Map map) {
		String output = "Traffic\n" + processTrafficHistory(map.getTiles());
		output += "Dirt\n" + processDirtHistory(map.getTiles());
		output += "Food\n" + processFoodHistory(map.getTiles());
		return output;
	}

	public static String processTrafficHistory(Tile[][] tiles) {
		String output = "";
		for(int i = 0; i < tiles.length; i++) {
			for(int j = 0; j < tiles[i].length; j++) {
				int traffic = 0;
				for(int k = 0; k < tiles[i][j].getHistory().size(); k++) {
					
					TileHistory history = tiles[i][j].getHistory().get(k);
					if(history.getAgent() != null) {
						traffic += 1;
					}
				}
				output += traffic + "\t";
			}
			output += "\n";
		}
		return output;
	}

	public static String processDirtHistory(Tile[][] tiles) {
		String output = "";
		
		for(int i = 0; i < tiles.length; i++) {
			for(int j = 0; j < tiles[i].length; j++) {
				int dirt = 0;
				for(int k = 0; k < tiles[i][j].getHistory().size(); k++) {
					TileHistory history = tiles[i][j].getHistory().get(k);
					if(history.getDirt() > dirt) {
						dirt = history.getDirt();
					}
				}
				output += dirt + "\t";
			}
			output += "\n";
		}
		return output;
	}

	public static String processFoodHistory(Tile[][] tiles) {
		String output = "";
		for(int i = 0; i < tiles.length; i++) {
			for(int j = 0; j < tiles[i].length; j++) {
				int food = 0;
				for(int k = 0; k < tiles[i][j].getHistory().size(); k++) {
					TileHistory history = tiles[i][j].getHistory().get(k);
					food += history.getFood();
				}
				output += food + "\t";
			}
			output += "\n";
		}
		return output;
	}
}
