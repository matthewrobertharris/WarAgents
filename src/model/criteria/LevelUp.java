package model.criteria;

import model.Agent;
import model.Map;
import model.Player;

public class LevelUp implements Criteria {

	private Player player;
	private int exp;

	public LevelUp(Player player, int exp) {
		setPlayer(player);
		setExp(exp);
	}

	public Player getPlayer() {
		return player;
	}

	public void setPlayer(Player player) {
		this.player = player;
	}

	public int getExp() {
		return exp;
	}

	public void setExp(int exp) {
		this.exp = exp;
	}

	@Override
	public boolean isFinished(Map map) throws Exception {
		for (Agent agent : getPlayer().getCurrentAgents()) {
			if (agent.getExp() >= getExp()) {
				return true;
			}
		}
		return false;
	}
	
	@Override
	public String toString() {
		String output = Condition.LEVEL_UP.toString();
		output += "\tPlayer=" + getPlayer().getName();
		output += "\tExp=" + getExp();
		return output;
	}

}
