package model.input.bool;

import model.Agent;
import model.Map;
import model.Tile;
import model.XY;
import model.input.DecisionBoolean;
import model.input.GetPosition;

public class HasEnemy extends DecisionBoolean {

	private GetPosition position;

	public HasEnemy(GetPosition position) {
		setPosition(position);
	}

	public GetPosition getPosition() {
		return position;
	}

	public void setPosition(GetPosition position) {
		this.position = position;
	}

	@Override
	public boolean decide(Agent agent, Map map) throws Exception {
		XY position = getPosition().getPosition(agent, map);
		Tile tile = map.getTile(position);
		Agent enemy = tile.getAgent();
		if(enemy != null) {
			return !enemy.getPlayer().getName().equals(agent.getPlayer().getName());
		}
		else {
			return false;
		}
	}
	
	public String toString() {
		String output = Option.HAS_ENEMY.toString() + " " + getPosition().toString();
		return output;
	}

}
