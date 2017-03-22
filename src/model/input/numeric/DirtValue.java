package model.input.numeric;

import model.Agent;
import model.Map;
import model.Tile;
import model.XY;
import model.input.DecisionNumeric;
import model.input.GetPosition;

public class DirtValue extends DecisionNumeric {

	private GetPosition position;

	public DirtValue(GetPosition position) {
		setPosition(position);
	}

	public GetPosition getPosition() {
		return position;
	}

	public void setPosition(GetPosition position) {
		this.position = position;
	}

	@Override
	public int decide(Agent agent, Map map) throws Exception {
		XY position = getPosition().getPosition(agent, map);
		Tile tile = map.getTile(position);
		return tile.getDirt();
	}
	
	public String toString() {
		String output = Option.DIRT_VALUE.toString() + " " + getPosition().toString();
		return output;
	}
}
