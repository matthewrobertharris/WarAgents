package model.criteria;

import model.Map;
import model.XY;

public class MapDirt implements Criteria {

	private XY position;
	private int dirt;

	public MapDirt(int dirt, XY position) {
		setDirt(dirt);
		setPosition(position);
	}

	public XY getPosition() {
		return position;
	}

	public void setPosition(XY position) {
		this.position = position;
	}

	public int getDirt() {
		return dirt;
	}

	public void setDirt(int dirt) {
		this.dirt = dirt;
	}

	@Override
	public boolean isFinished(Map map) throws Exception {
		if(map.isValid(getPosition())) {
			throw new Exception("Criteria position out of bounds");
		}
		return map.getTile(getPosition()).getDirt() == getDirt();
	}
	
	@Override
	public String toString() {
		String output = Condition.MAP_DIRT.toString();
		output += "\tPosition=" + getPosition().toString();
		output += "\tDirt=" + getDirt();
		return output;
	}
}
