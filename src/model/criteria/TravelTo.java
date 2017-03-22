package model.criteria;

import model.Agent;
import model.Map;
import model.Player;
import model.XY;

public class TravelTo implements Criteria {

	private XY position;
	private Player player;
	
	public TravelTo(Player player, XY position) {
		setPosition(position);
		setPlayer(player);
	}

	public Player getPlayer() {
		return player;
	}

	public void setPlayer(Player player) {
		this.player = player;
	}

	public XY getPosition() {
		return position;
	}

	public void setPosition(XY position) {
		this.position = position;
	}

	@Override
	public boolean isFinished(Map map) {
		try {
			for(Agent agent : getPlayer().getCurrentAgents()) {
				if(agent.getCurrentPos().equals(getPosition())) {
					return true;
				}
			}
		}
		catch (Exception e) {
			e.printStackTrace();
		}
		return false;
	}
	
	@Override
	public String toString() {
		String output = Condition.TRAVEL_TO.toString();
		output += "\tPlayer=" + getPlayer().getName();
		output += "\tPosition=" + getPosition().toString();
		return output;
	}

}
