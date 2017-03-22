package model;

public class Plant extends Thing {

	private static int idCounter;
	private int rate;
	private String ID;
	
	public Plant(int x, int y, int rate) {
		super("" + (idCounter++), x, y);
		setRate(rate);
	}

	public String getID() {
		return ID;
	}

	public void setID(String iD) {
		ID = iD;
	}

	public void update(Tile[][] map) {
		int x = getX();
		int y = getY();
		map[x][y].addFood(getRate() / 2);
		int spillOver = getRate() / 8;
		if (x > 0) {
			map[x - 1][y].addFood(spillOver);
		}
		if (x < (map.length - 1)) {
			map[x + 1][y].addFood(spillOver);
		}
		if (y > 0) {
			map[x][y - 1].addFood(spillOver);
		}
		
		if (getY() < (map[x].length - 1)) {
			map[x][y + 1].addFood(spillOver);
		}
	}

	public int getRate() {
		return rate;
	}

	public void setRate(int rate) {
		this.rate = rate;
	}
	
	public String toString() {
		String output = super.toString();
		output += " rate=" + getRate();
		return output;
	}
}
