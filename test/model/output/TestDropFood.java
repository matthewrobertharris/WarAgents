package model.output;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;

import org.junit.After;
import org.junit.Test;

import junit.framework.TestCase;
import main.Game;
import model.Agent;
import model.Map;
import model.Tile;
import model.output.Action.Activity;
import readers.ActionReaderImpl;
import readers.CriteriaReaderImpl;
import readers.GameReader;
import readers.GameReaderImpl;
import readers.InputReaderImpl;
import readers.MapReaderImpl;
import readers.ModeReaderImpl;
import readers.PlantReaderImpl;
import readers.PlayerReaderImpl;
import readers.PositionReaderImpl;
import readers.TreeReaderImpl;

public class TestDropFood extends TestCase {

	private GameReader gameReader;
	private final ByteArrayOutputStream outContent = new ByteArrayOutputStream();

	@Override
	protected void setUp() {
		gameReader = new GameReaderImpl(new MapReaderImpl(new PlantReaderImpl(),
				new PlayerReaderImpl(new TreeReaderImpl(new ActionReaderImpl(new PositionReaderImpl()), new InputReaderImpl(new PositionReaderImpl()))),
				new CriteriaReaderImpl(new ActionReaderImpl(new PositionReaderImpl())), new ModeReaderImpl()));
		System.setOut(new PrintStream(outContent));
	}
	
	@After
	public void cleanUpStreams() {
	    System.setOut(null);
	}

	/**
	 * http://stackoverflow.com/questions/1119385/junit-test-for-system-out-println
	 */
	@Test
	public void testDropFood_Success() {
		String file = "resources\\test\\outputMaps\\test_dropFood_success.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int newFood = 1;
		int prevFood = map.getTile(agent.getCurrentPos()).getFood();
		agent.setFood(newFood);
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.DROP_FOOD);
		assertTrue( map.getTile(agent.getCurrentPos()).getFood() == (prevFood + newFood));
	}
	
	@Test
	public void testDropFood_Success_MaxFood() {
		String file = "resources\\test\\outputMaps\\test_dropFood_success_maxFood.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int newFood = 1;
		agent.setFood(newFood);
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.DROP_FOOD);
		assertTrue( map.getTile(agent.getCurrentPos()).getFood() == Tile.MAX_FOOD);
	}
	
	@Test
	public void testDropFood_Fail_NoFood() {
		String file = "resources\\test\\outputMaps\\test_dropFood_fail_noFood.map";
		String error = "Cannot DROP_FOOD because agent has no food\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int newFood = 0;
		int prevFood = map.getTile(agent.getCurrentPos()).getFood();
		agent.setFood(newFood);
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.DROP_FOOD);
		assertTrue( map.getTile(agent.getCurrentPos()).getFood() == (prevFood + newFood));
		assertEquals(outContent.toString(), error);
	}	
	
	@Test
	public void test_ToString() {
		DropFood output = new DropFood();
		String strOutput = "DROP_FOOD";
		assertTrue(output.toString().equals(strOutput));
	}
}
