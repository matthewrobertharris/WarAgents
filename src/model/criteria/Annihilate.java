package model.criteria;

import model.Map;
import model.Player;

public class Annihilate implements Criteria {

	private Player player;
	
	public Annihilate(Player player) {
		setPlayer(player);
	}
	
	public Player getPlayer() {
		return player;
	}

	public void setPlayer(Player player) {
		this.player = player;
	}

	@Override
	public boolean isFinished(Map map) throws Exception {
		for(Player mapPlayer : map.getPlayers()) {
			if(mapPlayer.equals(getPlayer())) {
				if(mapPlayer.getCurrentAgents().size() == 0) {
					throw new Exception("Game Over.  No agents left");
				}
			}
			else {
				if(mapPlayer.getCurrentAgents().size() > 0) {
					return false;
				}
			}
		}
		return true;
	}
	
	@Override
	public String toString() {
		String output = Condition.ANNIHILATE.toString();
		output += "\tPlayer=" + getPlayer().getName();
		return output;
	}

}
