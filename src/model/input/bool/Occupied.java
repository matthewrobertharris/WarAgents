package model.input.bool;

import model.Agent;
import model.Map;
import model.Tile;
import model.XY;
import model.input.DecisionBoolean;
import model.input.GetPosition;

public class Occupied extends DecisionBoolean {

	private GetPosition position;

	public Occupied(GetPosition position) {
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
		if(tile != null) {
			return tile.isOccupied();
		}
		else {
			throw new Exception("Occupied: Position is out of bounds");
		}
	}

}
